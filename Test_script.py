import os
import re
import time
import json
import ccxt
import gspread
import pandas as pd
import talib
import requests  # HINZUGEFÜGT: Fehlender Import
from datetime import datetime
from typing import Dict, List, Any

# --- KONFIGURATION ---
COINS_TO_ANALYZE: Dict[str, Dict[str, str]] = {
    'Bitcoin': {'symbol': 'BTC'}, 'Ethereum': {'symbol': 'ETH'},
    'Solana': {'symbol': 'SOL'}, 'Cardano': {'symbol': 'ADA'},
    'Avalanche': {'symbol': 'AVAX'}, 'Chainlink': {'symbol': 'LINK'},
    'Polkadot': {'symbol': 'DOT'}, 'Dogecoin': {'symbol': 'DOGE'},
    'Toncoin': {'symbol': 'TON'}, 'Ethena': {'symbol': 'ENA'},
    'Ondo': {'symbol': 'ONDO'}, 'XRP': {'symbol': 'XRP'}, 
    'BNB': {'symbol': 'BNB'},
}

# --- HELFERFUNKTIONEN ---
def escape_html(text: Any) -> str:
    """Maskiert HTML-Sonderzeichen für Telegram HTML-Formatierung."""
    text = str(text)
    replacements = {'&': '&amp;', '<': '&lt;', '>': '&gt;'}
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

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
            f"{daten.get('wert_eur', 0):.2f}" if daten.get('wert_eur', 0) > 0 else "0"
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
    params = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der Telegram-Nachricht: {e.response.text if e.response else e}")

# --- API- & ANALYSE-FUNKTIONEN ---
def get_bitvavo_data(bitvavo, coin_name, symbol):
    """Holt historische Marktdaten von Bitvavo und berechnet den RSI."""
    try:
        markt_symbol = f'{symbol}/EUR'
        print(f"Starte Marktdatenabruf für {markt_symbol} von Bitvavo...")
        time.sleep(1.5) # Respektiert Rate-Limits (leicht erhöht zur Sicherheit)
        ohlcv = bitvavo.fetch_ohlcv(markt_symbol, '1d', limit=40)
        if len(ohlcv) < 40:
             return {'name': coin_name, 'error': f"Zu wenig historische Daten ({len(ohlcv)} Punkte)"}
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return {'name': coin_name, 'price': df['close'].iloc[-1], 'rsi': talib.RSI(df['close'], timeperiod=14).iloc[-1], 'error': None}
    except Exception as e:
        return {'name': coin_name, 'error': str(e)}

# --- HAUPTFUNKTION ---
def run_full_analysis():
    """Steuert den gesamten Analyseprozess."""
    print("Starte kompletten Analyse-Lauf...")
    api_key = os.getenv('BITVAVO_API_KEY')
    secret = os.getenv('BITVAVO_API_SECRET')
    if not api_key or not secret:
        print("Fehler: Bitvavo API-Schlüssel nicht gefunden!")
        sende_telegram_nachricht("Fehler: Bitvavo API-Schlüssel nicht in GitHub Secrets gefunden!")
        return
    
    try:
        bitvavo = ccxt.bitvavo({'apiKey': api_key, 'secret': secret})
        
        # Standard ccxt fetch_balance() gibt immer ein Dictionary zurück:
        # {'BTC': {'free': 0.001, 'used': 0, 'total': 0.001}, 'ETH': {...}, ...}
        balance_data = bitvavo.fetch_balance()
        print(f"Balance-Daten erfolgreich abgerufen: {len(balance_data)} Assets gefunden")
        
        # Vereinfachte und robuste Parsing-Logik für Standard ccxt-Format
        wallet_bestaende = {}
        for symbol, balance_info in balance_data.items():
            if isinstance(balance_info, dict) and balance_info.get('free', 0) > 0:
                wallet_bestaende[symbol] = balance_info['free']
        
        print(f"Erfolgreich {len(wallet_bestaende)} Coins mit Bestand gefunden: {list(wallet_bestaende.keys())}")
        
    except ccxt.AuthenticationError as e:
        print(f"Authentifizierungsfehler bei Bitvavo: {e}")
        sende_telegram_nachricht(f"🔐 <b>Bitvavo Authentifizierungsfehler</b>\n\nBitte API-Schlüssel überprüfen:\n<code>{escape_html(str(e))}</code>")
        return
    except ccxt.NetworkError as e:
        print(f"Netzwerkfehler bei Bitvavo: {e}")
        sende_telegram_nachricht(f"🌐 <b>Bitvavo Netzwerkfehler</b>\n\nVerbindungsproblem:\n<code>{escape_html(str(e))}</code>")
        return
    except Exception as e:
        print(f"Unerwarteter Fehler bei Bitvavo: {e}")
        print(f"Fehlertyp: {type(e)}")
        sende_telegram_nachricht(f"⚠️ <b>Unerwarteter Bitvavo-Fehler</b>\n\n<code>{escape_html(str(e))}</code>")
        return

    ergebnis_daten = []
    total_portfolio_wert = 0
    for coin_name, coin_data in COINS_TO_ANALYZE.items():
        symbol = coin_data['symbol']
        analyse_ergebnis = get_bitvavo_data(bitvavo, coin_name, symbol)
        
        bestand = wallet_bestaende.get(symbol, 0)
        analyse_ergebnis['bestand'] = bestand
        if not analyse_ergebnis.get('error'):
            wert_eur = bestand * analyse_ergebnis['price']
            analyse_ergebnis['wert_eur'] = wert_eur
            total_portfolio_wert += wert_eur
        
        ergebnis_daten.append(analyse_ergebnis)

    header = "<b>Tägliches Krypto-Analyse &amp; Portfolio Update</b> 🤖\n\n"
    nachrichten_teile = []
    for daten in ergebnis_daten:
        schreibe_in_google_sheet(daten)
        text_block = ""
        if daten.get('error'):
            text_block = f"<b>{escape_html(daten.get('name'))}</b>: ❌ Datenabruf fehlgeschlagen"
        else:
            status_text = "🟡 Neutral"
            if daten.get('rsi', 50) > 70: status_text = "🟢 Überkauft"
            elif daten.get('rsi', 50) < 30: status_text = "🔴 Überverkauft"
            symbol = next((coin_data['symbol'] for coin_name, coin_data in COINS_TO_ANALYZE.items() if coin_name == daten['name']), 'N/A')
            text_block = (f"<b>{escape_html(daten['name'])} ({escape_html(symbol)})</b>:\n"
                        f"<code>Preis: €{daten.get('price', 0):,.2f}</code> | <code>RSI: {daten.get('rsi', 0):.2f}</code>\n"
                        f"Status: {status_text}")
            if daten.get('bestand', 0) > 0:
                text_block += f"\n<b>Bestand</b>: <code>{daten['bestand']:.4f}</code> (<b>Wert: €{daten.get('wert_eur', 0):,.2f}</b>)"
        nachrichten_teile.append(text_block)

    footer = f"\n\n<b>Portfolio Gesamtwert</b>: <code>€{total_portfolio_wert:,.2f}</code>"
    separator = "\n" + "--------------------" + "\n"
    finale_nachricht = header + separator.join(nachrichten_teile) + footer
    sende_telegram_nachricht(finale_nachricht)
    print("Analyse-Lauf abgeschlossen.")

if __name__ == "__main__":
    run_full_analysis()
