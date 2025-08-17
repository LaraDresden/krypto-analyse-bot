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
    'Ethena': {'symbol': 'ENA'},   # Potenziell nicht unterstützt
    'Ondo': {'symbol': 'ONDO'},     # Potenziell nicht unterstützt
}

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
        
        # VERBESSERT: Bereitet die Zeile für Erfolg oder Fehler vor
        if daten.get('error'):
            neue_zeile = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                daten.get('name', 'N/A'),
                "N/A", "N/A", # Preis & RSI
                "Fehler",    # Status
                daten.get('error', 'Unbekannter Fehler') # Anmerkung
            ]
        else:
            neue_zeile = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                daten.get('name', 'N/A'),
                f"{daten.get('price', 0):.4f}",
                f"{daten.get('rsi', 0):.2f}",
                "Erfolgreich", # Status
                ""            # Anmerkung
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
        time.sleep(15) # WICHTIG: Pause *vor* dem API-Aufruf, um das Limit sicher einzuhalten
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
            'price': df['price'].iloc[-1], 'rsi': talib.RSI(df['price'], timeperiod=14).iloc[-1],
            'error': None
        }
    except Exception as e:
        print(f"Ein schwerer Fehler ist bei der Analyse von {coin_name} aufgetreten: {e}")
        return {'name': coin_name, 'error': str(e)}

def run_full_analysis():
    """Steuert den gesamten Analyseprozess."""
    # ... (sende_telegram_nachricht & escape_markdown hier einfügen, unverändert) ...
    # ...
    header = "*Tägliches Krypto-Analyse Update* 🤖\n\n"
    nachrichten_teile = []

    for daten in ergebnis_daten:
        # VERBESSERT: Macht die Fehlermeldung in Telegram "sprechend"
        if daten.get('error'):
            error_text = daten['error']
            # Kürzt lange Fehlermeldungen für eine bessere Lesbarkeit
            if len(error_text) > 100:
                error_text = error_text[:100] + "..."
            text_block = (f"*{escape_markdown(daten.get('name', 'Unbekannt'))}*\n"
                          f"❌ Analyse fehlgeschlagen\n"
                          f"`Grund: {escape_markdown(error_text)}`")
        else:
            # ... (Logik für Erfolgsfall bleibt gleich) ...
        nachrichten_teile.append(text_block)
    
    # ... (Rest der Funktion bleibt gleich) ...

# Fügen Sie hier die vollständigen, unveränderten Funktionen `sende_telegram_nachricht`
# und `escape_markdown` ein. Der Hauptaufruf am Ende bleibt ebenfalls gleich.
if __name__ == "__main__":
    run_full_analysis()
