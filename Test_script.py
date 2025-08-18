import os
import re
import time
import json
import ccxt
import gspread
import pandas as pd
import talib
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Dict, List, Any

# --- KONFIGURATION ---
COINS_TO_ANALYZE: Dict[str, Dict[str, str]] = {
    'Bitcoin': {'symbol': 'BTC'}, 'Ethereum': {'symbol': 'ETH'}, 'Solana': {'symbol': 'SOL'},
    'Cardano': {'symbol': 'ADA'}, 'Avalanche': {'symbol': 'AVAX'}, 'Chainlink': {'symbol': 'LINK'},
    'Polkadot': {'symbol': 'DOT'}, 'Dogecoin': {'symbol': 'DOGE'}, 'Toncoin': {'symbol': 'TON'},
    'Ethena': {'symbol': 'ENA'}, 'Ondo': {'symbol': 'ONDO'}, 'XRP': {'symbol': 'XRP'}, 'BNB': {'symbol': 'BNB'},
}

COIN_SEARCH_TERMS = {
    'Bitcoin': ['Bitcoin', 'BTC'], 'Ethereum': ['Ethereum', 'ETH', 'DeFi'], 'Solana': ['Solana', 'SOL'],
    'Cardano': ['Cardano', 'ADA'], 'Avalanche': ['Avalanche', 'AVAX'], 'Chainlink': ['Chainlink', 'LINK'],
    'Polkadot': ['Polkadot', 'DOT'], 'Dogecoin': ['Dogecoin', 'DOGE', 'Elon Musk'], 'Toncoin': ['Toncoin', 'TON'],
    'Ethena': ['Ethena', 'ENA'], 'Ondo': ['Ondo', 'ONDO'], 'XRP': ['XRP', 'Ripple', 'SEC'], 'BNB': ['BNB', 'Binance'],
}

QUALITY_SOURCES = ['coindesk.com', 'cointelegraph.com', 'reuters.com', 'bloomberg.com', 'cnbc.com', 'forbes.com', 'wsj.com', 'ft.com']
CRITICAL_KEYWORDS = ['SEC', 'lawsuit', 'ban', 'banned', 'regulation', 'hack', 'hacked', 'fraud', 'investigation', 'seized', 'arrest']

# --- HELFERFUNKTIONEN ---
def escape_html(text: Any) -> str:
    """Maskiert HTML-Sonderzeichen für Telegram."""
    text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def schreibe_in_google_sheet(daten: dict):
    """Schreibt das Ergebnis in das Google Sheet."""
    print(f"Protokolliere Ergebnis für {daten.get('name')}...")
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str: return
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        
        news_daten = daten.get('news_analyse', {})
        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), daten.get('name', 'N/A'),
            f"{daten.get('price', 0):.4f}" if daten.get('price') is not None else "N/A",
            f"{daten.get('rsi', 0):.2f}" if daten.get('rsi', 0) is not None else "N/A",
            f"{daten.get('macd', 0):.6f}" if daten.get('macd') is not None else "N/A",
            f"{daten.get('macd_signal', 0):.6f}" if daten.get('macd_signal') is not None else "N/A",
            f"{daten.get('macd_histogram', 0):.6f}" if daten.get('macd_histogram') is not None else "N/A",
            f"{daten.get('bb_position', 0):.1f}" if daten.get('bb_position') is not None else "N/A",
            f"{news_daten.get('sentiment_score', 0)}", news_daten.get('kategorie', 'Keine News'),
            news_daten.get('zusammenfassung', ''), "Ja" if news_daten.get('kritisch', False) else "Nein",
            "Erfolgreich" if not daten.get('error') else "Fehler", daten.get('error', ''),
            f"{daten.get('bestand', 0):.8f}" if daten.get('bestand') is not None else "0",
            f"{daten.get('wert_eur', 0):.2f}" if daten.get('wert_eur', 0) > 0 else "0"
        ]
        worksheet.append_row(row_data)
    except Exception as e:
        print(f"Fehler beim Schreiben in Google Sheet: {e}")

def sende_telegram_nachricht(nachricht: str):
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id: return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url, params=params, timeout=20)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Senden der Telegram-Nachricht: {e.response.text if e.response else e}")

# --- NEWS & AI ANALYSE FUNKTIONEN ---
def setup_gemini_ai():
    """Initialisiert die Gemini AI API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ FEHLER: GEMINI_API_KEY nicht gefunden!")
        return None
    
    print(f"🔑 Gemini API Key gefunden: {api_key[:20]}...")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        print("✅ Gemini AI erfolgreich initialisiert")
        return model
    except Exception as e:
        print(f"❌ FEHLER bei Gemini-Initialisierung: {e}")
        return None

def hole_aktuelle_news(coin_name: str) -> List[Dict]:
    """Holt aktuelle Nachrichten für einen Coin von NewsAPI."""
    api_key = os.getenv('NEWS_API_KEY')
    if not api_key: 
        print(f"⚠️ NEWS_API_KEY nicht gefunden für {coin_name}")
        return []
    
    print(f"🔑 News API Key für {coin_name}: {api_key[:20]}...")
    
    search_terms = COIN_SEARCH_TERMS.get(coin_name, [coin_name])
    gestern = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    all_articles = []
    
    for term in search_terms[:2]:
        try:
            url = f"https://newsapi.org/v2/everything?q={requests.utils.quote(term)}&language=en&from={gestern}&sortBy=relevancy&pageSize=5&apiKey={api_key}"
            print(f"📰 Suche News für '{term}'...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            articles = data.get('articles', [])
            print(f"📊 {len(articles)} Artikel gefunden für '{term}'")
            
            quality_articles = [a for a in articles if any(src in a.get('url', '') for src in QUALITY_SOURCES)]
            print(f"✅ {len(quality_articles)} Qualitäts-Artikel nach Filterung")
            all_articles.extend(quality_articles)
            time.sleep(0.5)  # Rate limiting
        except Exception as e:
            print(f"❌ FEHLER beim News-Abruf für '{term}': {e}")
    
    unique_articles = {a['title']: a for a in all_articles}.values()
    final_articles = sorted(list(unique_articles), key=lambda x: x.get('publishedAt'), reverse=True)[:3]
    print(f"🎯 Final: {len(final_articles)} einzigartige Artikel für {coin_name}")
    return final_articles

def analysiere_news_mit_ki(coin_name: str, news_artikel: List[Dict], model) -> Dict:
    """Analysiert News-Artikel mit Gemini AI für Sentiment und Kategorisierung."""
    if not model:
        print(f"❌ Kein Gemini Model für {coin_name}")
        return {}
    
    if not news_artikel:
        print(f"ℹ️ Keine News-Artikel für {coin_name}")
        return {}
    
    news_text = "\n".join([f"Titel: {a['title']}\nBeschreibung: {a.get('description', '')}" for a in news_artikel])
    print(f"📝 News-Text für {coin_name} ({len(news_text)} Zeichen): {news_text[:200]}...")
    
    prompt = f"""Analysiere die folgenden Nachrichten über {coin_name}: "{news_text}". 

Antworte AUSSCHLIESSLICH im folgenden JSON-Format:
{{
    "sentiment_score": [Zahl von -10 bis +10],
    "kategorie": "[Regulierung/Adoption/Technologie/Markt/Influencer/Andere]",
    "zusammenfassung": "[Kurze Zusammenfassung in max 8 Worten]",
    "kritisch": [true/false wenn SEC, Hack, Ban, etc.]
}}"""
    
    try:
        print(f"🤖 Sende Anfrage an Gemini für {coin_name}...")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"📨 Gemini Antwort für {coin_name}: {response_text}")
        
        # JSON extrahieren falls Markdown-Formatierung vorhanden
        if '```json' in response_text:
            response_text = re.search(r'```json\s*([\s\S]+?)\s*```', response_text).group(1)
            print(f"🔧 JSON aus Markdown extrahiert: {response_text}")
        elif '```' in response_text:
            response_text = re.search(r'```\s*([\s\S]+?)\s*```', response_text).group(1)
            print(f"🔧 Text aus Code-Block extrahiert: {response_text}")
        
        result = json.loads(response_text)
        print(f"✅ JSON erfolgreich geparst für {coin_name}: {result}")
        
        # Zusätzliche Kritisch-Prüfung mit Keywords
        result['kritisch'] = any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS) or result.get('kritisch', False)
        
        final_result = {
            'sentiment_score': max(-10, min(10, result.get('sentiment_score', 0))),
            'kategorie': result.get('kategorie', 'Andere'),
            'zusammenfassung': result.get('zusammenfassung', 'Diverse Nachrichten')[:50],
            'kritisch': result['kritisch']
        }
        print(f"🎯 Finales Ergebnis für {coin_name}: {final_result}")
        return final_result
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON-Parsing Fehler für {coin_name}: {e}")
        print(f"❌ Problematischer Text: {response_text}")
        return {
            'sentiment_score': 0,
            'kategorie': 'Andere',
            'zusammenfassung': 'JSON-Parsing fehlgeschlagen',
            'kritisch': any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS)
        }
    except Exception as e:
        print(f"❌ Allgemeiner Fehler bei KI-Analyse für {coin_name}: {e}")
        print(f"❌ Exception Typ: {type(e)}")
        return {
            'sentiment_score': 0,
            'kategorie': 'Andere',
            'zusammenfassung': 'KI-Analyse fehlgeschlagen',
            'kritisch': any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS)
        }

def interpretiere_technische_analyse(daten: dict) -> str:
    """Interpretiert die technischen Indikatoren kompakt."""
    if daten.get('error'): return "❌ Keine tech. Analyse"
    
    signals = []
    
    # RSI Interpretation
    if (rsi := daten.get('rsi', 50)) > 70: 
        signals.append("RSI:🔴Überkauft")
    elif rsi < 30: 
        signals.append("RSI:🟢Überverkauft")
    
    # MACD Interpretation mit Puffer
    if (macd_hist := daten.get('macd_histogram', 0)) > 0.0001: 
        signals.append("MACD:🟢Bullisch")
    elif macd_hist < -0.0001: 
        signals.append("MACD:🔴Bärisch")
    
    # Bollinger Bänder Interpretation
    if (bb_pos := daten.get('bb_position', 50)) > 80: 
        signals.append("BB:🔴Oberband")
    elif bb_pos < 20: 
        signals.append("BB:🟢Unterband")
    
    return " | ".join(signals) if signals else "🟡 Neutral"

def formatiere_news_analyse(news_daten: dict) -> str:
    """Formatiert die News-Analyse mit besseren Emojis."""
    if not news_daten or not news_daten.get('zusammenfassung'): return ""
    
    score = news_daten.get('sentiment_score', 0)
    kategorie = news_daten.get('kategorie', 'Andere')
    zusammenfassung = news_daten.get('zusammenfassung', '')
    kritisch = news_daten.get('kritisch', False)
    
    # Sentiment-Emoji basierend auf Score
    if score >= 7: sentiment_emoji = "🚀"
    elif score >= 3: sentiment_emoji = "😁"
    elif score >= 0: sentiment_emoji = "🙂"
    elif score >= -3: sentiment_emoji = "😞"
    else: sentiment_emoji = "😠"
    
    # Kritische Warnung
    warn_prefix = "⚠️ " if kritisch else ""
    
    return f"\n{warn_prefix}📰 {sentiment_emoji} {escape_html(zusammenfassung)} (*{escape_html(kategorie)}*)"

# --- TECHNISCHE ANALYSE ---
def get_bitvavo_data(bitvavo: ccxt.bitvavo, coin_name: str, symbol: str) -> dict:
    """Holt historische Marktdaten von Bitvavo und berechnet technische Indikatoren."""
    try:
        markt_symbol = f'{symbol}/EUR'
        print(f"Starte Marktdatenabruf für {markt_symbol}...")
        time.sleep(1.5)  # Rate limiting
        ohlcv = bitvavo.fetch_ohlcv(markt_symbol, '1d', limit=50)
        
        if len(ohlcv) < 34:  # Mindestanzahl für MACD(26) + RSI(14)
            return {'name': coin_name, 'error': f"Zu wenig Daten ({len(ohlcv)})"}
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        close = df['close']
        
        # Technische Indikatoren berechnen
        rsi = talib.RSI(close, timeperiod=14).iloc[-1]
        macd, macd_sig, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        bb_up, bb_mid, bb_low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        
        current_price = close.iloc[-1]
        bb_upper = bb_up.iloc[-1]
        bb_lower = bb_low.iloc[-1]
        
        # Bollinger Band Position (0-100%)
        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100 if (bb_upper - bb_lower) != 0 else 50
        
        return {
            'name': coin_name, 
            'price': current_price, 
            'rsi': rsi,
            'macd': macd.iloc[-1], 
            'macd_signal': macd_sig.iloc[-1], 
            'macd_histogram': macd_hist.iloc[-1],
            'bb_position': bb_position,
            'error': None
        }
        
    except Exception as e:
        return {'name': coin_name, 'error': str(e)}

# --- HAUPTFUNKTION ---
def run_full_analysis():
    """Steuert den gesamten Analyseprozess mit erweiterter News-Analyse."""
    print("🚀 Starte KI-verstärkten Analyse-Lauf...")
    
    # API-Schlüssel prüfen
    api_key = os.getenv('BITVAVO_API_KEY')
    secret = os.getenv('BITVAVO_API_SECRET')
    if not api_key or not secret:
        error_msg = "<b>Fehler:</b> Bitvavo API-Schlüssel nicht in GitHub Secrets gefunden!"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return
    
    # Gemini AI initialisieren
    gemini_model = setup_gemini_ai()
    if gemini_model:
        print("✅ Gemini AI erfolgreich initialisiert")
    else:
        print("⚠️ Gemini AI nicht verfügbar - News-Analyse deaktiviert")
    
    # Bitvavo-Verbindung und Portfolio-Daten
    wallet_bestaende = {}
    try:
        bitvavo = ccxt.bitvavo({'apiKey': api_key, 'secret': secret})
        balance_data = bitvavo.fetch_balance()
        print(f"Balance-Daten erfolgreich abgerufen: {len(balance_data)} Assets gefunden")
        
        # Standard ccxt-Format: {'BTC': {'free': 0.001, 'used': 0, 'total': 0.001}, ...}
        for symbol, balance_info in balance_data.items():
            if isinstance(balance_info, dict) and balance_info.get('free', 0) > 0:
                wallet_bestaende[symbol] = balance_info['free']
        
        print(f"✅ Erfolgreich {len(wallet_bestaende)} Coins mit Bestand gefunden: {list(wallet_bestaende.keys())}")
        
    except ccxt.AuthenticationError as e:
        error_msg = f"🔐 <b>Bitvavo Authentifizierungsfehler</b>\n\nBitte API-Schlüssel überprüfen:\n<code>{escape_html(str(e))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return
    except ccxt.NetworkError as e:
        error_msg = f"🌐 <b>Bitvavo Netzwerkfehler</b>\n\nVerbindungsproblem:\n<code>{escape_html(str(e))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return
    except Exception as e:
        error_msg = f"⚠️ <b>Unerwarteter Bitvavo-Fehler</b>\n\n<code>{escape_html(str(e))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return

    # Haupt-Analyse-Loop mit News-Integration
    ergebnis_daten = []
    total_portfolio_wert = 0
    kritische_alerts = []
    
    for coin_name, coin_data in COINS_TO_ANALYZE.items():
        symbol = coin_data['symbol']
        print(f"\n🔍 Analysiere {coin_name} ({symbol})...")
        
        # 1. Technische Analyse
        analyse_ergebnis = get_bitvavo_data(bitvavo, coin_name, symbol)
        
        # 2. News-Analyse (NEU!)
        if gemini_model and not analyse_ergebnis.get('error'):
            print(f"📰 Hole News für {coin_name}...")
            news_artikel = hole_aktuelle_news(coin_name)
            
            if news_artikel:
                print(f"📊 Analysiere {len(news_artikel)} News-Artikel mit KI...")
                news_analyse = analysiere_news_mit_ki(coin_name, news_artikel, gemini_model)
                analyse_ergebnis['news_analyse'] = news_analyse
                
                # Kritische Alerts sammeln
                if news_analyse.get('kritisch'):
                    kritische_alerts.append(f"<b>{coin_name}</b>: {news_analyse.get('zusammenfassung')}")
            else:
                print(f"ℹ️ Keine relevanten News für {coin_name} gefunden")
                analyse_ergebnis['news_analyse'] = {}
        else:
            analyse_ergebnis['news_analyse'] = {}
        
        # 3. Portfolio-Werte berechnen
        bestand = wallet_bestaende.get(symbol, 0)
        analyse_ergebnis['bestand'] = bestand
        if not analyse_ergebnis.get('error'):
            wert_eur = bestand * analyse_ergebnis['price']
            analyse_ergebnis['wert_eur'] = wert_eur
            total_portfolio_wert += wert_eur
        
        ergebnis_daten.append(analyse_ergebnis)
        time.sleep(0.5)  # Rate limiting zwischen Coins

    # Telegram-Nachricht erstellen mit News-Integration
    header = "<b>🚀 KI-Verstärkte Krypto-Analyse &amp; Portfolio Update</b> 🤖\n\n"
    
    # Kritische Alerts am Anfang
    if kritische_alerts:
        header += "⚠️ <b>KRITISCHE ALERTS:</b>\n"
        for alert in kritische_alerts:
            header += f"• {alert}\n"
        header += "\n" + "═" * 30 + "\n\n"
    
    nachrichten_teile = []
    for daten in ergebnis_daten:
        schreibe_in_google_sheet(daten)
        symbol = next((coin_data['symbol'] for coin_name, coin_data in COINS_TO_ANALYZE.items() if coin_name == daten['name']), 'N/A')
        
        text_block = f"<b>{escape_html(daten.get('name'))} ({escape_html(symbol)})</b>\n"

        if daten.get('error'):
            text_block += "❌ Datenabruf fehlgeschlagen"
        else:
            # Preis und technische Indikatoren
            text_block += f"<code>Preis: €{daten.get('price', 0):,.2f}</code>\n"
            
            # Technische Analyse kompakt
            tech_analyse_text = interpretiere_technische_analyse(daten)
            text_block += f"{tech_analyse_text}"
            
            # News-Analyse hinzufügen (NEU!)
            news_text = formatiere_news_analyse(daten.get('news_analyse'))
            if news_text:
                text_block += news_text
            
            # Portfolio-Info falls vorhanden
            if daten.get('bestand', 0) > 0:
                text_block += f"\n<b>💰 Bestand</b>: <code>{daten['bestand']:.4f}</code> (<b>€{daten.get('wert_eur', 0):,.2f}</b>)"
        
        nachrichten_teile.append(text_block)

    footer = f"\n\n<b>💼 Portfolio Gesamtwert</b>: <code>€{total_portfolio_wert:,.2f}</code>"
    
    # News-Status
    if gemini_model:
        footer += f"\n🤖 <b>KI-News-Analyse:</b> Aktiv"
    else:
        footer += f"\n⚠️ <b>News-Analyse:</b> Nicht verfügbar"
        
    separator = "\n" + "—" * 20 + "\n"
    finale_nachricht = header + separator.join(nachrichten_teile) + footer
    sende_telegram_nachricht(finale_nachricht)
    print("🎉 KI-verstärkte Analyse erfolgreich abgeschlossen!")

if __name__ == "__main__":
    run_full_analysis()
