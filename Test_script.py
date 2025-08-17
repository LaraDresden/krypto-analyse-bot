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
        
        # Reihenfolge entspricht den Google Sheets Spalten:
        # A: Zeitstempel | B: Coin_Name | C: Preis_EUR | D: RSI | E: MACD_Line | F: MACD_Signal 
        # G: MACD_Histogram | H: BB_Position_% | I: Status | J: Fehler_Details | K: Bestand | L: Wert_EUR
        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # A: Zeitstempel
            daten.get('name', 'N/A'),                      # B: Coin_Name
            f"{daten.get('price', 0):.4f}" if daten.get('price') is not None else "N/A",  # C: Preis_EUR
            f"{daten.get('rsi', 0):.2f}" if daten.get('rsi') is not None else "N/A",      # D: RSI
            f"{daten.get('macd', 0):.6f}" if daten.get('macd') is not None else "N/A",    # E: MACD_Line
            f"{daten.get('macd_signal', 0):.6f}" if daten.get('macd_signal') is not None else "N/A",  # F: MACD_Signal
            f"{daten.get('macd_histogram', 0):.6f}" if daten.get('macd_histogram') is not None else "N/A",  # G: MACD_Histogram
            f"{daten.get('bb_position', 0):.1f}" if daten.get('bb_position') is not None else "N/A",  # H: BB_Position_%
            "Erfolgreich" if not daten.get('error') else "Fehler",  # I: Status
            daten.get('error', ''),                        # J: Fehler_Details
            f"{daten.get('bestand', 0):.8f}" if daten.get('bestand') is not None else "0",  # K: Bestand
            f"{daten.get('wert_eur', 0):.2f}" if daten.get('wert_eur', 0) > 0 else "0"     # L: Wert_EUR
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

def interpretiere_technische_analyse(daten: dict) -> str:
    """Interpretiert die technischen Indikatoren und gibt eine Gesamteinschätzung zurück."""
    if daten.get('error'):
        return "❌ Keine Analyse möglich"
    
    signals = []
    
    # RSI Interpretation
    rsi = daten.get('rsi', 50)
    if rsi > 70:
        signals.append("RSI: 🔴 Überkauft")
    elif rsi < 30:
        signals.append("RSI: 🟢 Überverkauft")
    else:
        signals.append("RSI: 🟡 Neutral")
    
    # MACD Interpretation
    macd = daten.get('macd', 0)
    macd_signal = daten.get('macd_signal', 0)
    macd_hist = daten.get('macd_histogram', 0)
    
    if macd > macd_signal and macd_hist > 0:
        signals.append("MACD: 🟢 Bullisch")
    elif macd < macd_signal and macd_hist < 0:
        signals.append("MACD: 🔴 Bärisch") 
    else:
        signals.append("MACD: 🟡 Neutral")
    
    # Bollinger Bänder Interpretation
    bb_pos = daten.get('bb_position', 50)
    if bb_pos > 80:
        signals.append("BB: 🔴 Nahe Oberband")
    elif bb_pos < 20:
        signals.append("BB: 🟢 Nahe Unterband")
    else:
        signals.append("BB: 🟡 Mittelbereich")
    
    return " | ".join(signals)

# --- API- & ANALYSE-FUNKTIONEN ---
def get_bitvavo_data(bitvavo, coin_name, symbol):
    """Holt historische Marktdaten von Bitvavo und berechnet technische Indikatoren."""
    try:
        markt_symbol = f'{symbol}/EUR'
        print(f"Starte Marktdatenabruf für {markt_symbol} von Bitvavo...")
        time.sleep(1.5) # Respektiert Rate-Limits (leicht erhöht zur Sicherheit)
        ohlcv = bitvavo.fetch_ohlcv(markt_symbol, '1d', limit=50)  # Erhöht für MACD
        if len(ohlcv) < 50:
             return {'name': coin_name, 'error': f"Zu wenig historische Daten ({len(ohlcv)} Punkte)"}
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        close_prices = df['close']
        
        # Technische Indikatoren berechnen
        rsi = talib.RSI(close_prices, timeperiod=14).iloc[-1]
        
        # MACD (12, 26, 9)
        macd_line, macd_signal, macd_histogram = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
        macd = macd_line.iloc[-1]
        macd_sig = macd_signal.iloc[-1]
        macd_hist = macd_histogram.iloc[-1]
        
        # Bollinger Bänder (20 Perioden, 2 Standardabweichungen)
        bb_upper, bb_middle, bb_lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        current_price = close_prices.iloc[-1]
        bb_up = bb_upper.iloc[-1]
        bb_mid = bb_middle.iloc[-1]
        bb_low = bb_lower.iloc[-1]
        
        # Bollinger Band Position (0-100%, wo steht der Preis zwischen den Bändern)
        bb_position = ((current_price - bb_low) / (bb_up - bb_low)) * 100 if (bb_up - bb_low) != 0 else 50
        
        return {
            'name': coin_name, 
            'price': current_price,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_sig,
            'macd_histogram': macd_hist,
            'bb_upper': bb_up,
            'bb_middle': bb_mid,
            'bb_lower': bb_low,
            'bb_position': bb_position,
            'error': None
        }
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

    header = "<b>📊 Erweiterte Krypto-Analyse &amp; Portfolio Update</b> 🤖\n\n"
    nachrichten_teile = []
    for daten in ergebnis_daten:
        schreibe_in_google_sheet(daten)
        text_block = ""
        if daten.get('error'):
            text_block = f"<b>{escape_html(daten.get('name'))}</b>: ❌ Datenabruf fehlgeschlagen"
        else:
            symbol = next((coin_data['symbol'] for coin_name, coin_data in COINS_TO_ANALYZE.items() if coin_name == daten['name']), 'N/A')
            
            # Grundinformationen
            text_block = f"<b>{escape_html(daten['name'])} ({escape_html(symbol)})</b>\n"
            text_block += f"<code>Preis: €{daten.get('price', 0):,.2f}</code>\n"
            
            # Technische Indikatoren kompakt
            text_block += f"<code>RSI: {daten.get('rsi', 0):.1f}</code> | "
            text_block += f"<code>MACD: {daten.get('macd_histogram', 0):+.4f}</code> | "
            text_block += f"<code>BB: {daten.get('bb_position', 0):.0f}%</code>\n"
            
            # Interpretation
            analyse = interpretiere_technische_analyse(daten)
            text_block += f"{analyse}\n"
            
            # Portfolio-Info falls vorhanden
            if daten.get('bestand', 0) > 0:
                text_block += f"<b>💰 Bestand</b>: <code>{daten['bestand']:.4f}</code> (<b>€{daten.get('wert_eur', 0):,.2f}</b>)"
        
        nachrichten_teile.append(text_block)

    footer = f"\n\n<b>💼 Portfolio Gesamtwert</b>: <code>€{total_portfolio_wert:,.2f}</code>"
    separator = "\n" + "─" * 30 + "\n"
    finale_nachricht = header + separator.join(nachrichten_teile) + footer
    sende_telegram_nachricht(finale_nachricht)
    print("Analyse-Lauf abgeschlossen.")

if __name__ == "__main__":
    run_full_analysis()
