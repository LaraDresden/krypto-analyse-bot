import requests
import os
import pandas as pd
import talib
import re
import time
import gspread
import json
from datetime import datetime
from typing import Dict, List, Any

# --- KONFIGURATION ---
COINS_TO_ANALYZE: Dict[str, Dict[str, str]] = {
    'Bitcoin': {'symbol': 'BTC'},
    'Ethereum': {'symbol': 'ETH'},
    'Solana': {'symbol': 'SOL'},
    'Cardano': {'symbol': 'ADA'},
    'Avalanche': {'symbol': 'AVAX'},
    'Chainlink': {'symbol': 'LINK'},
    'Polygon': {'symbol': 'MATIC'},
    'Polkadot': {'symbol': 'DOT'},
    'Dogecoin': {'symbol': 'DOGE'},
    'Toncoin': {'symbol': 'TON'},
    'Ethena': {'symbol': 'ENA'},
    'Ondo': {'symbol': 'ONDO'},
}

def escape_markdown(text: Any) -> str:
    """Maskiert alle Sonderzeichen für Telegrams MarkdownV2."""
    text = str(text)
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

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
            daten.get('error', '')
        ]
        worksheet.append_row(row_data)
        print(f"Protokollierung für {daten.get('name')} abgeschlossen.")
    except Exception as e:
        print(f"Fehler beim Schreiben in Google Sheet: {e}")

def analysiere_coin(coin_name: str, coin_symbol: str) -> dict:
    """Holt und analysiert Daten für einen Coin und gibt ein Ergebnis-Dictionary zurück."""
    print(f"Starte Datenabruf für {coin_name} ({coin_symbol})...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key: 
        return {'name': coin_name, 'error': 'API-Schlüssel nicht gefunden!'}

    url = 'https://www.alphavantage.co/query'
    params = {'function': 'DIGITAL_CURRENCY_DAILY', 'symbol': coin_symbol, 'market': 'USD', 'apikey': api_key}
    
    try:
        time.sleep(15)
        response = requests.get(url, params=params)
        response.raise_for_status()
        daten = response.json()
        
        if 'Time Series (Digital Currency Daily)' not in daten:
            error_msg = daten.get('Note') or daten.get('Error Message', f"Ungültige Daten für {coin_name} empfangen.")
            print(f"Fehler bei {coin_name}: {error_msg}")
            return {'name': coin_name, 'error': error_msg}

        time_series = daten['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index').astype(float)
        df = df.rename(columns={'4. close': 'price'})
        df = df.sort_index(ascending=True)

        return {
            'name': coin_name, 'symbol': coin_symbol,
            'price': df['price'].iloc[-1], 
            'rsi': talib.RSI(df['price'], timeperiod=14).iloc[-1],
            'error': None
        }
    except Exception as e:
        print(f"Ein schwerer Fehler ist bei der Analyse von {coin_name} aufgetreten: {e}")
        return {'name': coin_name, 'error': str(e)}

def run_full_analysis():
    """Steuert den gesamten Analyseprozess."""
    ergebnis_daten: List[Dict] = []
    print("Starte komplette Portfolio-Analyse...")

    for coin_name, coin_data in COINS_TO_ANALYZE.items():
        analyse_ergebnis = analysiere_coin(coin_name, coin_data['symbol'])
        ergebnis_daten.append(analyse_ergebnis)
        schreibe_in_google_sheet(analyse_ergebnis)

    header = "*Tägliches Krypto-Analyse Update* 🤖\n\n"
    nachrichten_teile: List[str] = []

    for daten in ergebnis_daten:
        if daten.get('error'):
            error_text = daten['error']
            if len(error_text) > 100: 
                error_text = error_text[:100] + "..."
            text_block = (f"*{escape_markdown(daten.get('name', 'Unbekannt'))}*\n"
                          f"❌ Analyse fehlgeschlagen\n"
                          f"`Grund: {escape_markdown(error_text)}`")
        else:
            if daten['rsi'] > 70: 
                status_text = "🟢 Überkauft (Overbought)"
            elif daten['rsi'] < 30: 
                status_text = "🔴 Überverkauft (Oversold)"
            else: 
                status_text = "🟡 Neutral"
            
            text_block = (f"*{escape_markdown(daten['name'])} ({escape_markdown(daten['symbol'])})*\n"
                        f"Preis: `${daten['price']:,.4f}`\n"
                        f"RSI: `{daten['rsi']:.2f}`\n"
                        f"Status: {escape_markdown(status_text)}")
        
        nachrichten_teile.append(text_block)

    separator = "\n\n" + escape_markdown("--------------------") + "\n\n"
    finale_nachricht = header + separator.join(nachrichten_teile)
    
    sende_telegram_nachricht(finale_nachricht)
    print("Analyse-Lauf abgeschlossen.")

if __name__ == "__main__":
    run_full_analysis()
