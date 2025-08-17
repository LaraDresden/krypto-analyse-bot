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
        
        if daten.get('error'):
            neue_zeile = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                daten.get('name', 'N/A'), "N/A", "N/A", "Fehler",
                daten.get('error', 'Unbekannter Fehler')
            ]
        else:
            neue_zeile = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                daten.get('name', 'N/A'), f"{daten.get('price', 0):.4f}",
                f"{daten.get('rsi', 0):.2f}", "Erfolgreich", ""
            ]
        worksheet.append_row(neue_zeile)
        print(f"Protokollierung für {daten.get('name')} abgeschlossen.")
    except Exception as e:
        print(f"Fehler beim Schreiben in Google Sheet: {e}")

def analysiere_coin(coin_name: str, coin_symbol: str) -> dict:
    """Holt und analysiert Daten für einen Coin und gibt ein Ergebnis-Dictionary zurück."""
    print(f"Starte Datenabruf für {coin_name} ({coin_symbol})...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key: return {'name': coin_name, 'error': 'API-Schlüssel nicht gefunden!'}

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
