import requests
import os
import pandas as pd
import talib
import re
import time
import gspread
import json
import ccxt
from datetime import datetime
from typing import Dict, List, Any

# --- KONFIGURATION ---
COINS_TO_ANALYZE: Dict[str, Dict[str, str]] = {
    # Name: { AlphaVantage Symbol, Bitvavo Symbol }
    'Bitcoin': {'symbol_av': 'BTC', 'symbol_bv': 'BTC'},
    'Ethereum': {'symbol_av': 'ETH', 'symbol_bv': 'ETH'},
    'Solana': {'symbol_av': 'SOL', 'symbol_bv': 'SOL'},
    'Cardano': {'symbol_av': 'ADA', 'symbol_bv': 'ADA'},
    'Avalanche': {'symbol_av': 'AVAX', 'symbol_bv': 'AVAX'},
    'Chainlink': {'symbol_av': 'LINK', 'symbol_bv': 'LINK'},
    'Polygon': {'symbol_av': 'MATIC', 'symbol_bv': 'MATIC'},
    'Polkadot': {'symbol_av': 'DOT', 'symbol_bv': 'DOT'},
    'Dogecoin': {'symbol_av': 'DOGE', 'symbol_bv': 'DOGE'},
    'Toncoin': {'symbol_av': 'TON', 'symbol_bv': 'TON'},
    'Ethena': {'symbol_av': 'ENA', 'symbol_bv': 'ENA'},
    'Ondo': {'symbol_av': 'ONDO', 'symbol_bv': 'ONDO'},
}

# --- HELFERFUNKTIONEN ---
def escape_markdown(text: Any) -> str:
    """Maskiert alle Sonderzeichen für Telegrams MarkdownV2."""
    text = str(text)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# --- API-FUNKTIONEN ---
def get_bitvavo_balances() -> Dict[str, float]:
    """Stellt eine authentifizierte Verbindung zu Bitvavo her und ruft die Wallet-Bestände ab."""
    print("Verbinde mit Bitvavo, um Bestände abzurufen...")
    api_key = os.getenv('BITVAVO_API_KEY')
    secret = os.getenv('BITVAVO_API_SECRET')
    if not api_key or not secret:
        print("Fehler: Bitvavo API-Schlüssel nicht in GitHub Secrets gefunden!")
        return {}
    try:
        bitvavo = ccxt.bitvavo({'apiKey': api_key, 'secret': secret})
        balance_data = bitvavo.fetch_balance()
        holdings = {symbol: data['free'] for symbol, data in balance_data.items() if data['free'] > 0}
        print(f"Erfolgreich {len(holdings)} Coins mit Bestand auf Bitvavo gefunden.")
        return holdings
    except Exception as e:
        print(f"Fehler bei der Verbindung mit Bitvavo: {e}")
        return {}

def analysiere_coin(coin_name: str, coin_symbol_av: str) -> dict:
    """Holt Marktdaten von Alpha Vantage und analysiert sie."""
    print(f"Starte Marktdatenabruf für {coin_name}...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key: 
        return {'name': coin_name, 'error': 'API-Schlüssel nicht gefunden!'}

    url = 'https://www.alphavantage.co/query'
    params = {'function': 'DIGITAL_CURRENCY_DAILY', 'symbol': coin_symbol_av, 'market': 'USD', 'apikey': api_key}
    
    try:
        # Wichtige Pause *vor* dem API-Aufruf, um das Limit sicher einzuhalten
        time.sleep(15)
        response = requests.get(url, params=params)
        response.raise_for_status()
        daten = response.json()
        if 'Time Series (Digital Currency Daily)' not in daten:
            error_msg = daten.get('Note') or daten.get('Error Message', f"Ungültige Daten empfangen.")
            return {'name': coin_name, 'error': error_msg}

        time_series = daten['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index').astype(float)
        df = df.rename(columns={'4. close': 'price'})
        df = df.sort_index(ascending=True)

        return {
            'name': coin_name,
            'price': df['price'].iloc[-1], 
            'rsi': talib.RSI(df['price'], timeperiod=14).iloc[-1],
            'error': None
        }
    except Exception as e:
        return {'name': coin_name, 'error': str(e)}

# --- DATENBANK & BENACHRICHTIGUNG ---
def schreibe_in_google_sheet(daten: dict):
    """Schreibt das Ergebnis (Erfolg oder Fehler) in das Google Sheet."""
    print(f"Protokolliere Ergebnis für {daten.get('name')} in Google Sheet...")
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str: 
            print("Fehler: GOOGLE_CREDENTIALS Secret nicht gefunden!")
            return
            
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        
        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            daten.get('name', 'N/A'),
            f"{daten.get('price', 0):.4f}" if daten.get('price') is not None else "N/A",
            f"{daten.get('rsi', 0):.2f}" if daten.get('rsi') is not None else "N/A",
            "Erfolgreich" if not daten.get('error') else "Fehler",
            daten.get('error', ''),
            f"{daten.get('bestand', 0):.8f}" if daten.get('bestand') is not None else "0",
            f"{daten.get('wert_usd', 0):.2f}" if daten.get('wert_usd') is not None else "0"
        ]
        worksheet.append_row(row_data)
        print(f"Protokollierung für {daten.get('name')} abgeschlossen.")
    except Exception as e:
        print(f"Fehler beim Schreiben in Google Sheet: {e}")

def sende_telegram_nachricht(nachricht: str):
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id: 
        print("Fehler: Telegram-Zugangsdaten nicht gefunden!")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'MarkdownV2'}
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der Telegram-Nachricht: {e.response.text}")

# --- HAUPTFUNKTION ---
def run_full_analysis():
    """Steuert den gesamten Analyseprozess."""
    print("Starte kompletten Analyse-Lauf...")
    wallet_bestaende = get_bitvavo_balances()
    
    ergebnis_daten: List[Dict] = []
    total_portfolio_wert = 0

    for coin_name, coin_data in COINS_TO_ANALYZE.items():
        analyse_ergebnis = analysiere_coin(coin_name, coin_data['symbol_av'])
        
        bestand = wallet_bestaende.get(coin_data['symbol_bv'], 0)
        analyse_ergebnis['bestand'] = bestand
        if not analyse_ergebnis.get('error') and analyse_ergebnis.get('price') is not None:
            wert_usd = bestand * analyse_ergebnis['price']
            analyse_ergebnis['wert_usd'] = wert_usd
            total_portfolio_wert += wert_usd
        
        ergebnis_daten.append(analyse_ergebnis)

    header = "*Tägliches Krypto-Analyse & Portfolio Update* 🤖\n\n"
    nachrichten_teile: List[str] = []

    for daten in ergebnis_daten:
        schreibe_in_google_sheet(daten)
        text_block = ""
        if daten.get('error'):
            text_block = f"*{escape_markdown(daten.get('name'))}*: ❌ Analyse fehlgeschlagen (`{escape_markdown(daten['error'][:50])}`)"
        else:
            status_text = "🟡 Neutral"
            if daten['rsi'] > 70: status_text = "🟢 Überkauft"
            elif daten['rsi'] < 30: status_text = "🔴 Überverkauft"
            
            text_block = (f"*{escape_markdown(daten['name'])} ({escape_markdown(daten.get('symbol_av', ''))})*:\n"
                        f"`Preis: ${daten.get('price', 0):,.2f}` | `RSI: {daten.get('rsi', 0):.2f}`\n"
                        f"Status: {escape_markdown(status_text)}")
            if daten.get('bestand', 0) > 0:
                text_block += f"\n*Bestand*: `{daten['bestand']:.4f}` (*Wert: ${daten.get('wert_usd', 0):,.2f}*)"

        nachrichten_teile.append(text_block)

    footer = f"\n\n*Portfolio Gesamtwert*: `${total_portfolio_wert:,.2f}`"
    separator = "\n" + escape_markdown("--------------------") + "\n"
    finale_nachricht = header + separator.join(nachrichten_teile) + footer
    
    sende_telegram_nachricht(finale_nachricht)
    print("Analyse-Lauf abgeschlossen.")

if __name__ == "__main__":
    run_full_analysis()
