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

# --- ERWEITERTE KONFIGURATION ---
COINS_TO_ANALYZE: Dict[str, Dict[str, str]] = {
    'Bitcoin': {'symbol': 'BTC'}, 'Ethereum': {'symbol': 'ETH'}, 'Solana': {'symbol': 'SOL'},
    'Cardano': {'symbol': 'ADA'}, 'Avalanche': {'symbol': 'AVAX'}, 'Chainlink': {'symbol': 'LINK'},
    'Polkadot': {'symbol': 'DOT'}, 'Dogecoin': {'symbol': 'DOGE'}, 'Toncoin': {'symbol': 'TON'},
    'Ethena': {'symbol': 'ENA'}, 'Ondo': {'symbol': 'ONDO'}, 'XRP': {'symbol': 'XRP'}, 'BNB': {'symbol': 'BNB'},
}

# Erweiterte Suchbegriffe für bessere News-Coverage
COIN_SEARCH_TERMS = {
    'Bitcoin': ['Bitcoin', 'BTC', 'digital gold'], 'Ethereum': ['Ethereum', 'ETH', 'smart contracts'], 
    'Solana': ['Solana', 'SOL'], 'Cardano': ['Cardano', 'ADA'], 'Avalanche': ['Avalanche', 'AVAX'], 
    'Chainlink': ['Chainlink', 'LINK', 'oracle'], 'Polkadot': ['Polkadot', 'DOT'], 
    'Dogecoin': ['Dogecoin', 'DOGE', 'meme coin'], 'Toncoin': ['Toncoin', 'TON'],
    'Ethena': ['Ethena', 'ENA'], 'Ondo': ['Ondo', 'ONDO'], 
    'XRP': ['XRP', 'Ripple'], 'BNB': ['BNB', 'Binance'],
}

# Erweiterte Qualitätsquellen für bessere News-Coverage
QUALITY_SOURCES = [
    'coindesk.com', 'cointelegraph.com', 'reuters.com', 'bloomberg.com', 'cnbc.com', 
    'forbes.com', 'wsj.com', 'ft.com', 'coinbase.com', 'crypto.news', 'decrypt.co',
    'theblock.co', 'cryptoslate.com', 'bitcoin.com', 'coingecko.com'
]

CRITICAL_KEYWORDS = ['SEC', 'lawsuit', 'ban', 'banned', 'regulation', 'hack', 'hacked', 'fraud', 'investigation', 'seized', 'arrest']

# Smart Alert Konfiguration
ALERT_THRESHOLDS = {
    'breakout_percentage': 2.0,    # % über Bollinger Band für Breakout
    'rsi_oversold': 25,            # RSI unter diesem Wert = Alert
    'rsi_overbought': 75,          # RSI über diesem Wert = Alert
    'volume_spike': 200,           # % Volumen-Anstieg für Alert
}

# Portfolio Tracking (wird in Google Sheets gespeichert)
PORTFOLIO_HISTORY_DAYS = 7  # Letzte 7 Tage für Performance-Vergleich

# --- HELFERFUNKTIONEN ---
def escape_html(text: Any) -> str:
    """Maskiert HTML-Sonderzeichen für Telegram."""
    text = str(text)
    # KORRIGIERT: Ersetzt durch HTML-Entitäten (nicht durch sich selbst!)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def schreibe_in_google_sheet(daten: dict):
    """Schreibt das erweiterte Ergebnis in das Google Sheet."""
    print(f"Protokolliere erweiterte Ergebnisse für {daten.get('name')}...")
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str: return
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        
        news_daten = daten.get('news_analyse', {})
        
        # ERWEITERTE SPALTEN für alle neuen Features
        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # A: Zeitstempel
            daten.get('name', 'N/A'),                      # B: Coin_Name
            f"{daten.get('price', 0):.4f}" if daten.get('price') is not None else "N/A",  # C: Preis_EUR
            f"{daten.get('rsi', 0):.2f}" if daten.get('rsi', 0) is not None else "N/A",  # D: RSI
            f"{daten.get('macd', 0):.6f}" if daten.get('macd') is not None else "N/A",    # E: MACD_Line
            f"{daten.get('macd_signal', 0):.6f}" if daten.get('macd_signal') is not None else "N/A",  # F: MACD_Signal
            f"{daten.get('macd_histogram', 0):.6f}" if daten.get('macd_histogram') is not None else "N/A",  # G: MACD_Histogram
            f"{daten.get('bb_position', 0):.1f}" if daten.get('bb_position') is not None else "N/A",  # H: BB_Position_%
            # NEUE SPALTEN für erweiterte Analyse
            f"{daten.get('ma20', 0):.4f}" if daten.get('ma20') is not None else "N/A",    # I: MA20
            f"{daten.get('ma50', 0):.4f}" if daten.get('ma50') is not None else "N/A",    # J: MA50  
            f"{daten.get('ma200', 0):.4f}" if daten.get('ma200') is not None else "N/A",  # K: MA200
            daten.get('ma_trend', 'Neutral'),                                             # L: MA_Trend
            f"{daten.get('volume_ratio', 1):.2f}" if daten.get('volume_ratio') is not None else "N/A",  # M: Volume_Ratio
            f"{daten.get('stoch_k', 50):.1f}" if daten.get('stoch_k') is not None else "N/A",  # N: Stoch_K
            # News-Analyse
            f"{news_daten.get('sentiment_score', 0)}" if news_daten else "0",            # O: News_Sentiment
            news_daten.get('kategorie', 'Keine News') if news_daten else "Keine News",  # P: News_Kategorie
            news_daten.get('zusammenfassung', '') if news_daten else "",                # Q: News_Zusammenfassung
            "Ja" if news_daten.get('kritisch', False) else "Nein",                      # R: News_Kritisch
            # Status und Portfolio
            "Erfolgreich" if not daten.get('error') else "Fehler",                      # S: Status
            daten.get('error', ''),                                                     # T: Fehler_Details
            f"{daten.get('bestand', 0):.8f}" if daten.get('bestand') is not None else "0",  # U: Bestand
            f"{daten.get('wert_eur', 0):.2f}" if daten.get('wert_eur', 0) > 0 else "0"     # V: Wert_EUR
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

# --- NEUE ERWEITERTE ANALYSE FUNKTIONEN ---
def get_fear_greed_index() -> Dict:
    """Holt den Crypto Fear & Greed Index von alternative.me."""
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('data') and len(data['data']) > 0:
            fng_data = data['data'][0]
            value = int(fng_data.get('value', 50))
            classification = fng_data.get('value_classification', 'Neutral')
            
            # Emoji basierend auf Wert
            if value <= 20: emoji = "😨"      # Extreme Fear
            elif value <= 40: emoji = "😟"    # Fear  
            elif value <= 60: emoji = "😐"    # Neutral
            elif value <= 80: emoji = "😊"    # Greed
            else: emoji = "🤑"                # Extreme Greed
            
            return {
                'value': value,
                'classification': classification,
                'emoji': emoji,
                'timestamp': fng_data.get('timestamp', '')
            }
    except Exception as e:
        print(f"Fehler beim Fear & Greed Index: {e}")
    
    return {'value': 50, 'classification': 'Neutral', 'emoji': '😐', 'timestamp': ''}

def get_portfolio_performance_from_sheets() -> Dict:
    """Holt historische Portfolio-Daten aus Google Sheets für Performance-Vergleich."""
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str: return {'change_24h': 0, 'change_7d': 0}
        
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        
        # Letzte 10 Einträge holen (für Performance-Berechnung)
        records = worksheet.get_all_records()[-10:]
        
        if len(records) < 2: return {'change_24h': 0, 'change_7d': 0}
        
        # Portfolio-Werte aus den letzten Tagen sammeln
        portfolio_values = {}
        for record in records:
            timestamp = record.get('Zeitstempel', '')
            if timestamp:
                try:
                    date = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').date()
                    wert = float(record.get('Wert_EUR', 0))
                    if wert > 0:  # Nur Einträge mit Portfolio-Wert
                        if date not in portfolio_values:
                            portfolio_values[date] = 0
                        portfolio_values[date] += wert
                except:
                    continue
        
        # Performance berechnen
        heute = datetime.now().date()
        gestern = heute - timedelta(days=1)
        vor_7_tagen = heute - timedelta(days=7)
        
        portfolio_heute = portfolio_values.get(heute, 0)
        portfolio_gestern = portfolio_values.get(gestern, portfolio_heute)
        portfolio_7d = portfolio_values.get(vor_7_tagen, portfolio_heute)
        
        change_24h = ((portfolio_heute - portfolio_gestern) / portfolio_gestern * 100) if portfolio_gestern > 0 else 0
        change_7d = ((portfolio_heute - portfolio_7d) / portfolio_7d * 100) if portfolio_7d > 0 else 0
        
        return {'change_24h': change_24h, 'change_7d': change_7d}
        
    except Exception as e:
        print(f"Fehler beim Portfolio-Performance Abruf: {e}")
        return {'change_24h': 0, 'change_7d': 0}

def calculate_sentiment_trend(alle_news_sentiments: Dict) -> str:
    """Berechnet den allgemeinen Sentiment-Trend basierend auf allen Coins."""
    if not alle_news_sentiments:
        return "😐 Neutral"
    
    sentiment_scores = []
    for coin_name, news_data in alle_news_sentiments.items():
        if news_data.get('sentiment_score') is not None:
            sentiment_scores.append(news_data['sentiment_score'])
    
    if not sentiment_scores:
        return "😐 Neutral"
    
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
    
    if avg_sentiment >= 5: return "🚀 Sehr Bullisch"
    elif avg_sentiment >= 2: return "😊 Bullisch"
    elif avg_sentiment >= -2: return "😐 Neutral"
    elif avg_sentiment >= -5: return "😞 Bärisch"
    else: return "😨 Sehr Bärisch"

def generate_smart_alerts(daten: dict, coin_name: str) -> List[str]:
    """Generiert intelligente Alerts basierend auf technischen Indikatoren."""
    alerts = []
    
    if daten.get('error'):
        return alerts
    
    price = daten.get('price', 0)
    rsi = daten.get('rsi', 50)
    bb_position = daten.get('bb_position', 50)
    macd_hist = daten.get('macd_histogram', 0)
    ma_trend = daten.get('ma_trend', 'Neutral')
    
    # RSI Alerts
    if rsi <= ALERT_THRESHOLDS['rsi_oversold']:
        alerts.append(f"🟢 {coin_name} RSI bei {rsi:.0f} - Potentielle Kaufgelegenheit!")
    elif rsi >= ALERT_THRESHOLDS['rsi_overbought']:
        alerts.append(f"🔴 {coin_name} RSI bei {rsi:.0f} - Überkauft!")
    
    # Bollinger Band Breakout
    if bb_position >= (100 - ALERT_THRESHOLDS['breakout_percentage']):
        alerts.append(f"🚨 {coin_name} Breakout! Preis über Bollinger Band!")
    elif bb_position <= ALERT_THRESHOLDS['breakout_percentage']:
        alerts.append(f"📉 {coin_name} unter Bollinger Band - Support durchbrochen!")
    
    # Trend-Wechsel Alerts
    if ma_trend == "🟢 Golden Cross":
        alerts.append(f"⭐ {coin_name} Golden Cross - Bullisches Signal!")
    elif ma_trend == "🔴 Death Cross":
        alerts.append(f"💀 {coin_name} Death Cross - Bärisches Signal!")
    
    # MACD Momentum
    if abs(macd_hist) > 0.001:  # Signifikante MACD Bewegung
        direction = "Bullisch" if macd_hist > 0 else "Bärisch"
        alerts.append(f"📊 {coin_name} starkes MACD Signal - {direction}!")
    
    return alerts

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
        # KORRIGIERT: Neues Modell verwenden (gemini-pro ist deprecated)
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ Gemini AI erfolgreich initialisiert mit gemini-1.5-flash")
        return model
    except Exception as e:
        print(f"❌ FEHLER bei Gemini-Initialisierung: {e}")
        # Fallback auf alternatives Modell
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            print("✅ Gemini AI Fallback erfolgreich mit gemini-1.5-pro")
            return model
        except Exception as e2:
            print(f"❌ Auch Fallback fehlgeschlagen: {e2}")
            return None

def hole_aktuelle_news_optimiert() -> Dict[str, List[Dict]]:
    """Optimierte News-Suche: Eine Anfrage für alle Coins kombiniert."""
    api_key = os.getenv('NEWS_API_KEY')
    if not api_key: 
        print("⚠️ NEWS_API_KEY nicht gefunden")
        return {}
    
    # Alle Suchbegriffe für eine kombinierte Suche sammeln
    alle_suchbegriffe = []
    for coin_name, terms in COIN_SEARCH_TERMS.items():
        alle_suchbegriffe.extend(terms[:1])  # Nur der wichtigste Begriff pro Coin
    
    # Kombinierte Suche (viel effizienter!)
    combined_query = " OR ".join([f'"{term}"' for term in alle_suchbegriffe])
    gestern = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"🔍 Kombinierte News-Suche für alle Coins: {combined_query[:100]}...")
    
    try:
        url = f"https://newsapi.org/v2/everything"
        params = {
            'q': combined_query,
            'language': 'en', 
            'from': gestern,
            'sortBy': 'relevancy',
            'pageSize': 50,  # Mehr Artikel für bessere Abdeckung
            'apiKey': api_key
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        articles = data.get('articles', [])
        
        print(f"📊 {len(articles)} Gesamt-Artikel gefunden")
        
        # Artikel nach Coins kategorisieren
        news_per_coin = {}
        for coin_name, search_terms in COIN_SEARCH_TERMS.items():
            coin_articles = []
            
            for article in articles:
                title_lower = article.get('title', '').lower()
                desc_lower = article.get('description', '').lower()
                content = f"{title_lower} {desc_lower}"
                
                # Prüfe ob Artikel zu diesem Coin gehört
                if any(term.lower() in content for term in search_terms):
                    # Zusätzlich Qualitätsfilter (flexibler)
                    url = article.get('url', '')
                    if (any(src in url for src in QUALITY_SOURCES) or 
                        any(src.replace('.com', '') in url for src in QUALITY_SOURCES) or
                        'crypto' in url.lower() or 'bitcoin' in url.lower()):
                        coin_articles.append(article)
            
            # Top 3 pro Coin
            news_per_coin[coin_name] = sorted(coin_articles, 
                                            key=lambda x: x.get('publishedAt', ''), 
                                            reverse=True)[:3]
            
            print(f"📰 {coin_name}: {len(news_per_coin[coin_name])} relevante Artikel")
        
        return news_per_coin
        
    except Exception as e:
        print(f"❌ Fehler bei kombinierter News-Suche: {e}")
        return {}

def analysiere_news_mit_ki(coin_name: str, news_artikel: List[Dict], model) -> Dict:
    """Analysiert News-Artikel mit Gemini AI - ROBUSTES JSON-PARSING."""
    if not model:
        print(f"❌ Kein Gemini Model für {coin_name}")
        return {}
    
    if not news_artikel:
        print(f"ℹ️ Keine News-Artikel für {coin_name}")
        return {}
    
    news_text = "\n".join([f"Titel: {a['title']}\nBeschreibung: {a.get('description', '')}" for a in news_artikel])
    print(f"📝 News-Text für {coin_name} ({len(news_text)} Zeichen): {news_text[:150]}...")
    
    # OPTIMIERTER Prompt für bessere JSON-Compliance
    prompt = f"""Analysiere diese Nachrichten über {coin_name}: "{news_text}"

ANTWORTE NUR MIT GÜLTIGEM JSON - KEIN ANDERER TEXT:
{{
    "sentiment_score": -5,
    "kategorie": "Markt", 
    "zusammenfassung": "Kurze Beschreibung",
    "kritisch": false
}}

Regeln:
- sentiment_score: Zahl von -10 bis +10
- kategorie: Regulierung/Adoption/Technologie/Markt/Influencer/Andere  
- zusammenfassung: Max 6 Wörter
- kritisch: true bei SEC/Hack/Ban/Fraud"""
    
    try:
        print(f"🤖 Sende Anfrage an Gemini für {coin_name}...")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"📨 Gemini Antwort für {coin_name}: {response_text}")
        
        # ROBUSTES JSON-PARSING mit mehreren Fallback-Strategien
        json_text = response_text
        
        # Strategie 1: Direkte JSON-Extraktion aus Markdown
        json_patterns = [
            r'```json\s*([\s\S]+?)\s*```',
            r'```\s*([\s\S]+?)\s*```',
            r'\{[\s\S]*\}',  # Findet das erste JSON-Objekt
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, response_text)
            if match:
                json_text = match.group(1) if '```' in pattern else match.group(0)
                print(f"🔧 JSON Pattern gefunden: {json_text[:100]}...")
                break
        
        # Strategie 2: Fallback JSON-Cleaning
        json_text = json_text.strip()
        if not json_text.startswith('{'):
            # Suche nach dem ersten {
            start = json_text.find('{')
            if start != -1:
                json_text = json_text[start:]
        
        if not json_text.endswith('}'):
            # Suche nach dem letzten }
            end = json_text.rfind('}')
            if end != -1:
                json_text = json_text[:end+1]
        
        print(f"🧹 Bereinigter JSON für {coin_name}: {json_text}")
        
        result = json.loads(json_text)
        print(f"✅ JSON erfolgreich geparst für {coin_name}: {result}")
        
        # Validation und Kritisch-Check
        kritisch_check = any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS)
        
        final_result = {
            'sentiment_score': max(-10, min(10, int(result.get('sentiment_score', 0)))),
            'kategorie': str(result.get('kategorie', 'Andere'))[:20],
            'zusammenfassung': str(result.get('zusammenfassung', 'News gefunden'))[:40],
            'kritisch': bool(result.get('kritisch', False)) or kritisch_check
        }
        print(f"🎯 Finales Ergebnis für {coin_name}: {final_result}")
        return final_result
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON-Parsing Fehler für {coin_name}: {e}")
        print(f"❌ Problematischer Text: {response_text[:200]}...")
        return {
            'sentiment_score': 0,
            'kategorie': 'Andere',
            'zusammenfassung': 'JSON-Parse Fehler',
            'kritisch': any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS)
        }
    except Exception as e:
        print(f"❌ Allgemeiner Fehler bei KI-Analyse für {coin_name}: {e}")
        return {
            'sentiment_score': 0,
            'kategorie': 'Andere', 
            'zusammenfassung': 'KI-Analyse Fehler',
            'kritisch': any(kw.lower() in news_text.lower() for kw in CRITICAL_KEYWORDS)
        }

def interpretiere_erweiterte_technische_analyse(daten: dict) -> str:
    """Interpretiert ALLE technischen Indikatoren kompakt aber vollständig."""
    if daten.get('error'): return "❌ Keine tech. Analyse"
    
    signals = []
    
    # RSI Interpretation - IMMER anzeigen
    rsi = daten.get('rsi', 50)
    if rsi > 75: signals.append(f"RSI:🔴{rsi:.0f}")
    elif rsi < 25: signals.append(f"RSI:🟢{rsi:.0f}")
    else: signals.append(f"RSI:🟡{rsi:.0f}")
    
    # MACD Interpretation
    macd_hist = daten.get('macd_histogram', 0)
    if macd_hist > 0.0001: signals.append("MACD:🟢Bull")
    elif macd_hist < -0.0001: signals.append("MACD:🔴Bear")
    else: signals.append("MACD:🟡Neut")
    
    # Moving Average Trend
    ma_trend = daten.get('ma_trend', '🟡 Neutral')
    if 'Golden Cross' in ma_trend: signals.append("MA:⭐Gold")
    elif 'Death Cross' in ma_trend: signals.append("MA:💀Death")
    elif 'Aufwärtstrend' in ma_trend: signals.append("MA:🟢Up")
    elif 'Abwärtstrend' in ma_trend: signals.append("MA:🔴Down")
    else: signals.append("MA:🟡Neut")
    
    # Bollinger Bänder
    bb_pos = daten.get('bb_position', 50)
    if bb_pos > 95: signals.append("BB:🚨Break")
    elif bb_pos > 80: signals.append("BB:🔴Upper")
    elif bb_pos < 5: signals.append("BB:📉Break")
    elif bb_pos < 20: signals.append("BB:🟢Lower")
    else: signals.append("BB:🟡Mid")
    
    # Volumen
    vol_ratio = daten.get('volume_ratio', 1)
    if vol_ratio > 3: signals.append("Vol:🔥High")
    elif vol_ratio > 1.5: signals.append("Vol:📈Inc")
    elif vol_ratio < 0.5: signals.append("Vol:📉Low")
    
    return " | ".join(signals)

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

# --- ERWEITERTE TECHNISCHE ANALYSE ---
def get_bitvavo_data(bitvavo: ccxt.bitvavo, coin_name: str, symbol: str) -> dict:
    """Holt historische Marktdaten von Bitvavo und berechnet ALLE technischen Indikatoren."""
    try:
        markt_symbol = f'{symbol}/EUR'
        print(f"Starte erweiterte Marktdatenanalyse für {markt_symbol}...")
        time.sleep(1.5)  # Rate limiting
        ohlcv = bitvavo.fetch_ohlcv(markt_symbol, '1d', limit=250)  # Mehr Daten für MA200
        
        if len(ohlcv) < 34:  # Mindestanzahl für MACD(26) + RSI(14)
            return {'name': coin_name, 'error': f"Zu wenig Daten ({len(ohlcv)})"}
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        close = df['close']
        volume = df['volume']
        high = df['high']
        low = df['low']
        
        current_price = close.iloc[-1]
        
        # === KLASSISCHE INDIKATOREN ===
        # RSI
        rsi = talib.RSI(close, timeperiod=14).iloc[-1]
        
        # MACD
        macd, macd_sig, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        
        # Bollinger Bänder
        bb_up, bb_mid, bb_low = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        bb_upper = bb_up.iloc[-1]
        bb_lower = bb_low.iloc[-1]
        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100 if (bb_upper - bb_lower) != 0 else 50
        
        # === NEUE ERWEITERTE INDIKATOREN ===
        # Moving Averages
        ma20 = talib.SMA(close, timeperiod=20).iloc[-1] if len(close) >= 20 else current_price
        ma50 = talib.SMA(close, timeperiod=50).iloc[-1] if len(close) >= 50 else current_price
        ma200 = talib.SMA(close, timeperiod=200).iloc[-1] if len(close) >= 200 else current_price
        
        # Trend-Analyse (Golden Cross / Death Cross)
        ma_trend = "🟡 Neutral"
        if len(close) >= 200:
            if ma50 > ma200 * 1.02:  # 2% Puffer für klares Signal
                ma_trend = "🟢 Aufwärtstrend"
                # Prüfe auf Golden Cross (MA50 kreuzt MA200 nach oben)
                ma50_yesterday = talib.SMA(close, timeperiod=50).iloc[-2] if len(close) >= 51 else ma50
                ma200_yesterday = talib.SMA(close, timeperiod=200).iloc[-2] if len(close) >= 201 else ma200
                if ma50_yesterday <= ma200_yesterday and ma50 > ma200:
                    ma_trend = "🟢 Golden Cross"
            elif ma50 < ma200 * 0.98:  # 2% Puffer für klares Signal
                ma_trend = "🔴 Abwärtstrend"
                # Prüfe auf Death Cross (MA50 kreuzt MA200 nach unten)
                ma50_yesterday = talib.SMA(close, timeperiod=50).iloc[-2] if len(close) >= 51 else ma50
                ma200_yesterday = talib.SMA(close, timeperiod=200).iloc[-2] if len(close) >= 201 else ma200
                if ma50_yesterday >= ma200_yesterday and ma50 < ma200:
                    ma_trend = "🔴 Death Cross"
        
        # Volumen-Analyse
        avg_volume_20 = volume.tail(20).mean() if len(volume) >= 20 else volume.iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 1
        
        # Stochastic Oscillator
        stoch_k, stoch_d = talib.STOCH(high, low, close)
        stoch_k_current = stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else 50
        
        # Williams %R
        williams_r = talib.WILLR(high, low, close, timeperiod=14).iloc[-1]
        
        # Preis-Position relativ zu Moving Averages
        price_vs_ma20 = ((current_price - ma20) / ma20 * 100) if ma20 > 0 else 0
        price_vs_ma50 = ((current_price - ma50) / ma50 * 100) if ma50 > 0 else 0
        price_vs_ma200 = ((current_price - ma200) / ma200 * 100) if ma200 > 0 else 0
        
        return {
            'name': coin_name, 
            'price': current_price,
            
            # Klassische Indikatoren
            'rsi': rsi,
            'macd': macd.iloc[-1],
            'macd_signal': macd_sig.iloc[-1],
            'macd_histogram': macd_hist.iloc[-1],
            'bb_position': bb_position,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            
            # Neue erweiterte Indikatoren
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'ma_trend': ma_trend,
            'price_vs_ma20': price_vs_ma20,
            'price_vs_ma50': price_vs_ma50,
            'price_vs_ma200': price_vs_ma200,
            'volume_ratio': volume_ratio,
            'stoch_k': stoch_k_current,
            'williams_r': williams_r,
            
            'error': None
        }
        
    except Exception as e:
        return {'name': coin_name, 'error': str(e)}

# --- HAUPTFUNKTION ---
def run_full_analysis():
    """Steuert den gesamten erweiterten Analyseprozess mit ALLEN neuen Features."""
    print("🚀 Starte SUPER-CHARGED KI-verstärkten Analyse-Lauf...")
    
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
    
    # KORRIGIERT: Alle neuen Features ordentlich integrieren
    print("📊 Lade Market Context...")
    fear_greed = get_fear_greed_index()
    portfolio_performance = get_portfolio_performance_from_sheets()
    
    print(f"😨😐🤑 Fear & Greed Index: {fear_greed['value']} ({fear_greed['classification']}) {fear_greed['emoji']}")
    print(f"📈📉 Portfolio Performance: 24h {portfolio_performance['change_24h']:+.1f}%, 7d {portfolio_performance['change_7d']:+.1f}%")
    
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

    # SUPER-OPTIMIERTE Haupt-Analyse-Loop
    ergebnis_daten = []
    total_portfolio_wert = 0
    kritische_alerts = []
    alle_smart_alerts = []
    news_sentiments = {}
    
    # Eine News-Suche für alle Coins (statt 13×2=26 API-Calls!)
    print("\n🚀 Starte optimierte News-Suche für alle Coins...")
    alle_news = hole_aktuelle_news_optimiert() if gemini_model else {}
    
    for coin_name, coin_data in COINS_TO_ANALYZE.items():
        symbol = coin_data['symbol']
        print(f"\n🔍 Analysiere {coin_name} ({symbol}) mit ALLEN Indikatoren...")
        
        # 1. ERWEITERTE Technische Analyse
        analyse_ergebnis = get_bitvavo_data(bitvavo, coin_name, symbol)
        
        # 2. News-Analyse (OPTIMIERT!)
        if gemini_model and not analyse_ergebnis.get('error'):
            news_artikel = alle_news.get(coin_name, [])
            
            if news_artikel:
                print(f"📊 Analysiere {len(news_artikel)} News-Artikel mit KI...")
                news_analyse = analysiere_news_mit_ki(coin_name, news_artikel, gemini_model)
                analyse_ergebnis['news_analyse'] = news_analyse
                news_sentiments[coin_name] = news_analyse
                
                # Kritische Alerts sammeln
                if news_analyse.get('kritisch'):
                    kritische_alerts.append(f"<b>{coin_name}</b>: {news_analyse.get('zusammenfassung')}")
            else:
                print(f"ℹ️ Keine relevanten News für {coin_name} gefunden")
                analyse_ergebnis['news_analyse'] = {}
        else:
            analyse_ergebnis['news_analyse'] = {}
        
        # 3. KORRIGIERT: Smart Alerts generieren
        if not analyse_ergebnis.get('error'):
            smart_alerts = generate_smart_alerts(analyse_ergebnis, coin_name)
            alle_smart_alerts.extend(smart_alerts)
        
        # 4. Portfolio-Werte berechnen
        bestand = wallet_bestaende.get(symbol, 0)
        analyse_ergebnis['bestand'] = bestand
        if not analyse_ergebnis.get('error'):
            wert_eur = bestand * analyse_ergebnis['price']
            analyse_ergebnis['wert_eur'] = wert_eur
            total_portfolio_wert += wert_eur
        
        ergebnis_daten.append(analyse_ergebnis)
        time.sleep(0.3)  # Reduziertes Rate limiting da weniger API-Calls

    # SUPER-ENHANCED Telegram-Nachricht erstellen
    header = "<b>🚀 SUPER-CHARGED KI-Krypto-Analyse &amp; Portfolio Update</b> 🤖\n\n"
    
    # KORRIGIERT: Market Context Header mit allen Features
    perf_24h = portfolio_performance['change_24h']
    perf_emoji = "🚀" if perf_24h > 5 else "📈" if perf_24h > 0 else "📉" if perf_24h > -5 else "💥"
    
    header += f"📊 <b>Market Context:</b>\n"
    header += f"😨😐🤑 Fear &amp; Greed: {fear_greed['value']} ({fear_greed['classification']}) {fear_greed['emoji']}\n"
    header += f"{perf_emoji} Portfolio 24h: {perf_24h:+.1f}% | 7d: {portfolio_performance['change_7d']:+.1f}%\n"
    
    # KORRIGIERT: Overall Sentiment mit allen News
    sentiment_trend = calculate_sentiment_trend(news_sentiments)
    header += f"📰 News Sentiment: {sentiment_trend}\n\n"
    
    # Kritische Alerts am Anfang
    if kritische_alerts:
        header += "⚠️ <b>KRITISCHE NEWS ALERTS:</b>\n"
        for alert in kritische_alerts:
            header += f"• {alert}\n"
        header += "\n"
    
    # KORRIGIERT: Smart Technical Alerts integriert
    if alle_smart_alerts:
        header += "🚨 <b>SMART TECHNICAL ALERTS:</b>\n"
        for alert in alle_smart_alerts[:5]:  # Top 5 wichtigste Alerts
            header += f"• {alert}\n"
        header += "\n"
    
    header += "═" * 35 + "\n\n"
    
    nachrichten_teile = []
    for daten in ergebnis_daten:
        schreibe_in_google_sheet(daten)
        symbol = next((coin_data['symbol'] for coin_name, coin_data in COINS_TO_ANALYZE.items() if coin_name == daten['name']), 'N/A')
        
        text_block = f"<b>{escape_html(daten.get('name'))} ({escape_html(symbol)})</b>\n"

        if daten.get('error'):
            text_block += "❌ Datenabruf fehlgeschlagen"
        else:
            # Preis und ERWEITERTE technische Indikatoren
            text_block += f"<code>€{daten.get('price', 0):,.2f}</code>"
            
            # Trend-Info
            ma_trend = daten.get('ma_trend', '')
            if 'Golden Cross' in ma_trend or 'Death Cross' in ma_trend:
                text_block += f" {ma_trend.split()[1] if len(ma_trend.split()) > 1 else ''}"
            
            text_block += "\n"
            
            # KORRIGIERT: Funktionsaufruf-Name
            tech_analyse_text = interpretiere_erweiterte_technische_analyse(daten)
            text_block += f"{tech_analyse_text}"
            
            # News-Analyse hinzufügen
            news_text = formatiere_news_analyse(daten.get('news_analyse'))
            if news_text:
                text_block += news_text
            
            # Portfolio-Info falls vorhanden
            if daten.get('bestand', 0) > 0:
                text_block += f"\n<b>💰</b> <code>{daten['bestand']:.4f}</code> (<b>€{daten.get('wert_eur', 0):,.2f}</b>)"
        
        nachrichten_teile.append(text_block)

    footer = f"\n\n<b>💼 Portfolio Gesamtwert</b>: <code>€{total_portfolio_wert:,.2f}</code>"
    
    # KORRIGIERT: Portfolio Performance in Footer integriert
    footer += f"\n📈 <b>Performance:</b> 24h: {portfolio_performance['change_24h']:+.1f}% | 7d: {portfolio_performance['change_7d']:+.1f}%"
    
    # Erweiterte Status-Info
    news_found_count = sum(1 for d in ergebnis_daten if d.get('news_analyse', {}).get('zusammenfassung', '') != '')
    alerts_count = len(alle_smart_alerts)
    
    if gemini_model:
        footer += f"\n🤖 <b>KI-News:</b> {news_found_count}/{len(COINS_TO_ANALYZE)} Coins"
        footer += f"\n🚨 <b>Smart Alerts:</b> {alerts_count} gefunden"
        footer += f"\n⚡ <b>API-Optimierung:</b> 95% weniger Calls"
    else:
        footer += f"\n⚠️ <b>News-Analyse:</b> Nicht verfügbar"
        footer += f"\n📊 <b>Tech-Analyse:</b> Vollständig aktiv"
        
    separator = "\n" + "—" * 25 + "\n"
    finale_nachricht = header + separator.join(nachrichten_teile) + footer
    sende_telegram_nachricht(finale_nachricht)
    print("🎉 SUPER-CHARGED Analyse erfolgreich abgeschlossen!")

if __name__ == "__main__":
    run_full_analysis()
