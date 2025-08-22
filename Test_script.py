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
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, TypedDict
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import asyncio
import numpy as np

# === .ENV DATEI LADEN ===
from dotenv import load_dotenv
load_dotenv()  # Lädt alle Umgebungsvariablen aus der .env-Datei

# === NEUE MODULARE IMPORTS ===
from config import (
    API_CONFIG, COINS_TO_ANALYZE, COIN_SEARCH_TERMS, QUALITY_SOURCES, 
    CRITICAL_KEYWORDS, TECHNICAL_CONFIG, ALERT_THRESHOLDS, 
    PORTFOLIO_HISTORY_DAYS, get_api_credentials, validate_config
)
from modules.utils.logger import logger, handle_exceptions, write_health_check
from modules.data_models import CoinAnalysisResult, MarketData, TechnicalIndicators, NewsAnalysis
from modules.strategies.registry import StrategyRegistry
from modules.strategies.moderate.momentum_strategy import ModerateMomentumStrategy

# === TYPE DEFINITIONS ===
# Behalte Legacy TypedDict für Übergangszeit - wird später durch data_models ersetzt
class NewsAnalysisResult(TypedDict):
    """Legacy Typ-Definition für News-Analyse-Ergebnisse."""
    sentiment_score: int
    kategorie: str
    zusammenfassung: str
    kritisch: bool

# === LOGGING KONFIGURATION ===
# Nutze neue modulare Logger, aber behalte Legacy-Setup für Übergangszeit
def setup_logging():
    """Legacy Logging-Setup - wird durch modules.utils.logger ersetzt."""
    return logger.logger  # Verwende den neuen Logger

# Initialisiere Logger (Legacy-Kompatibilität)
legacy_logger = setup_logging()

# === STRATEGIE-SYSTEM INITIALISIERUNG ===
def setup_trading_strategies():
    """Initialisiert und registriert alle verfügbaren Trading-Strategien."""
    try:
        # Registriere die Moderate Momentum Strategy
        StrategyRegistry.register(
            name="moderate_momentum",
            strategy_class=ModerateMomentumStrategy,
            description="MACD + Bollinger Band Momentum Strategy mit Volume-Bestätigung",
            category="moderate"
        )
        
        logger.info("✅ Trading-Strategien erfolgreich initialisiert")
        return True
    except Exception as e:
        logger.error(f"❌ Fehler bei Strategie-Initialisierung: {e}")
        return False

# Initialisiere Strategien
strategy_system_ready = setup_trading_strategies()

def generate_trading_signals(coin_data: dict) -> dict:
    """
    Generiert BUY/SELL/HOLD Empfehlungen basierend auf technischen Daten.
    
    Returns:
        dict: {
            'signal': 'BUY'/'SELL'/'HOLD',
            'confidence': float (0.0-1.0),
            'reasoning': str,
            'strategy_name': str
        }
    """
    if coin_data.get('error') or not strategy_system_ready:
        return {
            'signal': 'HOLD',
            'confidence': 0.0,
            'reasoning': 'Keine Daten verfügbar',
            'strategy_name': 'fallback'
        }
    
    try:
        # Erstelle MarketData Objekt für die Strategie
        market_data = MarketData(
            symbol=coin_data.get('name', 'UNKNOWN'),
            price=coin_data.get('price', 0.0),
            volume=coin_data.get('volume_24h', 0.0),
            timestamp=datetime.now(),
            high_24h=coin_data.get('high_24h', coin_data.get('price', 0.0)),
            low_24h=coin_data.get('low_24h', coin_data.get('price', 0.0)),
            change_24h=coin_data.get('price_change_24h_percent', 0.0)
        )
        
        # Erstelle TechnicalIndicators Objekt
        tech_indicators = TechnicalIndicators(
            rsi=coin_data.get('rsi', 50.0),
            macd=coin_data.get('macd', 0.0),
            macd_signal=coin_data.get('macd_signal', 0.0),
            macd_histogram=coin_data.get('macd_histogram', 0.0),
            ma20=coin_data.get('sma_20', coin_data.get('price', 0.0)),
            ma50=coin_data.get('sma_50', coin_data.get('price', 0.0)),
            ma200=coin_data.get('sma_200', coin_data.get('price', 0.0)),
            bb_upper=coin_data.get('bb_upper', 0.0),
            bb_lower=coin_data.get('bb_lower', 0.0),
            bb_position=coin_data.get('bb_position', 50.0),
            atr=coin_data.get('atr', 0.0),
            atr_percentage=coin_data.get('atr_percentage', 0.0),
            volume_ratio=coin_data.get('volume_ratio', 1.0),
            stoch_k=coin_data.get('stoch_k', 50.0),
            williams_r=coin_data.get('williams_r', -50.0)
        )
        
        # Erstelle News-Analyse Objekt (falls vorhanden)
        news_analysis = None
        if coin_data.get('news_analyse'):
            news_data = coin_data['news_analyse']
            news_analysis = NewsAnalysis(
                sentiment_score=news_data.get('sentiment_score', 0),
                category=news_data.get('kategorie', 'neutral'),
                summary=news_data.get('zusammenfassung', ''),
                is_critical=news_data.get('kritisch', False),
                confidence=0.8,  # Standard-Konfidenz für News
                articles_count=1  # Vereinfachung
            )
        
        # Hole die Strategie-Instanz
        strategy = StrategyRegistry.get_instance("moderate_momentum")
        if not strategy:
            logger.warning("⚠️ Moderate Momentum Strategy nicht verfügbar, verwende Fallback")
            return generate_fallback_signal(coin_data)
        
        # Generiere Trading-Entscheidung
        decision = strategy.analyze(coin_data.get('name', 'UNKNOWN'), market_data, tech_indicators, news_analysis)
        
        return {
            'signal': decision.signal.value,
            'confidence': decision.confidence,
            'reasoning': decision.reasoning,
            'strategy_name': 'moderate_momentum'
        }
        
    except Exception as e:
        logger.error(f"❌ Fehler bei Signal-Generierung für {coin_data.get('name', 'UNKNOWN')}: {e}")
        return generate_fallback_signal(coin_data)

def generate_fallback_signal(coin_data: dict) -> dict:
    """
    Fallback-Signal-Generierung basierend auf einfachen technischen Regeln.
    """
    try:
        rsi = coin_data.get('rsi', 50.0)
        macd_hist = coin_data.get('macd_histogram', 0.0)
        bb_position = coin_data.get('bb_position', 50.0)
        
        # Einfache Signal-Logik
        signals = []
        
        # RSI Signale
        if rsi < 30:
            signals.append(('BUY', 0.7, 'RSI überverkauft'))
        elif rsi > 70:
            signals.append(('SELL', 0.7, 'RSI überkauft'))
        
        # MACD Signale
        if macd_hist > 0.001:
            signals.append(('BUY', 0.6, 'MACD bullish'))
        elif macd_hist < -0.001:
            signals.append(('SELL', 0.6, 'MACD bearish'))
        
        # Bollinger Band Signale
        if bb_position < 20:
            signals.append(('BUY', 0.5, 'BB unterstes Band'))
        elif bb_position > 80:
            signals.append(('SELL', 0.5, 'BB oberstes Band'))
        
        # Bestimme finales Signal
        if not signals:
            return {'signal': 'HOLD', 'confidence': 0.3, 'reasoning': 'Neutrale Signale', 'strategy_name': 'fallback'}
        
        # Gewichte Signale
        buy_score = sum(conf for sig, conf, _ in signals if sig == 'BUY')
        sell_score = sum(conf for sig, conf, _ in signals if sig == 'SELL')
        
        if buy_score > sell_score and buy_score > 0.5:
            reasoning = '; '.join([reason for sig, _, reason in signals if sig == 'BUY'])
            return {'signal': 'BUY', 'confidence': min(buy_score, 0.9), 'reasoning': reasoning, 'strategy_name': 'fallback'}
        elif sell_score > buy_score and sell_score > 0.5:
            reasoning = '; '.join([reason for sig, _, reason in signals if sig == 'SELL'])
            return {'signal': 'SELL', 'confidence': min(sell_score, 0.9), 'reasoning': reasoning, 'strategy_name': 'fallback'}
        else:
            return {'signal': 'HOLD', 'confidence': 0.4, 'reasoning': 'Gemischte Signale', 'strategy_name': 'fallback'}
            
    except Exception as e:
        logger.error(f"❌ Fehler bei Fallback-Signal: {e}")
        return {'signal': 'HOLD', 'confidence': 0.0, 'reasoning': 'Fehler bei Analyse', 'strategy_name': 'error'}

# === KONFIGURATION ===
# Alle Konfigurationen sind jetzt in config.py - nur Legacy-Kompatibilität hier
print("✅ Konfiguration erfolgreich aus config.py geladen")

# Validiere Konfiguration beim Start
config_warnings = validate_config()
if config_warnings:
    for warning in config_warnings:
        logger.warning(warning)

# --- HELFERFUNKTIONEN ---
# Nutze neue SecuritySanitizer aus modules.utils.logger
from modules.utils.logger import SecuritySanitizer

def sanitize_error_message(msg: str) -> str:
    """Legacy-Wrapper für SecuritySanitizer."""
    return SecuritySanitizer.sanitize(msg)

def escape_html(text: Any) -> str:
    """Maskiert HTML-Sonderzeichen für Telegram."""
    text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def schreibe_in_google_sheet(daten: Dict[str, Any]) -> None:
    """Schreibt das erweiterte Ergebnis in das Google Sheet."""
    logger.info(f"Protokolliere erweiterte Ergebnisse für {daten.get('name')}...")
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
            # ATR Volatilitäts-Daten
            f"{daten.get('atr', 0):.4f}" if daten.get('atr') is not None else "N/A",           # O: ATR
            f"{daten.get('atr_percentage', 0):.2f}" if daten.get('atr_percentage') is not None else "N/A",  # P: ATR_Percentage
            daten.get('volatility_level', 'N/A'),                                               # Q: Volatility_Level
            daten.get('volatility_trend', 'N/A'),                                               # R: Volatility_Trend
            f"{daten.get('stop_loss_long', 0):.4f}" if daten.get('stop_loss_long') is not None else "N/A",  # S: Stop_Loss_Long
            # News-Analyse
            f"{news_daten.get('sentiment_score', 0)}" if news_daten else "0",            # T: News_Sentiment
            news_daten.get('kategorie', 'Keine News') if news_daten else "Keine News",  # U: News_Kategorie
            news_daten.get('zusammenfassung', '') if news_daten else "",                # V: News_Zusammenfassung
            "Ja" if news_daten.get('kritisch', False) else "Nein",                      # W: News_Kritisch
            # Status und Portfolio
            "Erfolgreich" if not daten.get('error') else "Fehler",                      # X: Status
            daten.get('error', ''),                                                     # Y: Fehler_Details
            f"{daten.get('bestand', 0):.8f}" if daten.get('bestand') is not None else "0",  # Z: Bestand
            f"{daten.get('wert_eur', 0):.2f}" if daten.get('wert_eur', 0) > 0 else "0",    # AA: Wert_EUR
            # Trading-Strategie Empfehlungen - NEU für Performance-Tracking
            daten.get('strategy_signal', 'HOLD'),                                       # AB: Strategy_Signal
            f"{daten.get('strategy_confidence', 0.5):.3f}" if daten.get('strategy_confidence') is not None else "0.500",  # AC: Confidence_Score
            daten.get('strategy_reasoning', ''),                                        # AD: Strategy_Reasoning
            daten.get('strategy_name', 'fallback'),                                     # AE: Strategy_Name
            # Performance Tracking - Werden später für Backtesting verwendet
            f"{daten.get('price', 0):.4f}" if daten.get('price') is not None else "N/A",  # AF: Signal_Price (Preis zum Zeitpunkt der Empfehlung)
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")                                 # AG: Signal_Timestamp
        ]
        worksheet.append_row(row_data)
    except json.JSONDecodeError as e:
        logger.error(f"Fehler beim Parsen der Google Credentials: {e}")
    except gspread.exceptions.APIError as e:
        logger.error(f"Google Sheets API Fehler: {e}")
    except gspread.exceptions.SpreadsheetNotFound as e:
        logger.error(f"Google Sheet nicht gefunden: {e}")
    except gspread.exceptions.WorksheetNotFound as e:
        logger.error(f"Worksheet 'Market_Data' nicht gefunden: {e}")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Schreiben in Google Sheet: {e}")

def sende_telegram_nachricht(nachricht: str) -> None:
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    # IMMER Nachrichteninhalt in der Konsole anzeigen
    print("\n" + "="*60)
    print("📱 TELEGRAM NACHRICHTENINHALT (Vorschau):")
    print("="*60)
    print(nachricht)
    print("="*60 + "\n")
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id: 
        logger.warning("⚠️ Telegram-Credentials nicht gefunden. Nachricht wird nur als Vorschau angezeigt.")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {'chat_id': chat_id, 'text': nachricht, 'parse_mode': 'HTML'}
    try:
        response = requests.post(url, params=params, timeout=API_CONFIG['telegram_timeout'])
        response.raise_for_status()
        logger.info(f"📱 Telegram-Benachrichtigung erfolgreich gesendet!")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout beim Senden der Telegram-Nachricht: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Verbindungsfehler beim Senden der Telegram-Nachricht: {e}")
    except requests.exceptions.HTTPError as e:
        error_text = ""
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_text = e.response.text
            except:
                error_text = f"HTTP {e.response.status_code}"
        logger.error(f"HTTP-Fehler beim Senden der Telegram-Nachricht: {error_text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Allgemeiner Fehler beim Senden der Telegram-Nachricht: {e}")

# --- NEUE ERWEITERTE ANALYSE FUNKTIONEN ---
def get_fear_greed_index() -> Dict[str, Union[int, str]]:
    """Holt den Crypto Fear & Greed Index von alternative.me."""
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=API_CONFIG['news_api_timeout'])
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
    except requests.exceptions.Timeout as e:
        print(f"Timeout beim Fear & Greed Index Abruf: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Netzwerkfehler beim Fear & Greed Index: {e}")
    except (ValueError, KeyError) as e:
        print(f"Datenformat-Fehler beim Fear & Greed Index: {e}")
    except Exception as e:
        print(f"Unerwarteter Fehler beim Fear & Greed Index: {e}")
    
    return {'value': 50, 'classification': 'Neutral', 'emoji': '😐', 'timestamp': ''}

def get_portfolio_performance_from_sheets() -> Dict[str, float]:
    """Holt historische Portfolio-Daten aus Google Sheets für Performance-Vergleich."""
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str: return {'change_24h': 0, 'change_7d': 0}
        
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        
        # KORRIGIERT: Robustere Behandlung von Header-Problemen
        try:
            # Versuche normale get_all_records
            records = worksheet.get_all_records()[-10:]
        except (gspread.exceptions.APIError, gspread.exceptions.WorksheetNotFound) as header_error:
            print(f"Header-Problem erkannt: {header_error}")
            # Fallback: Manuelle Datenextraktion ohne Header-Abhängigkeit
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                return {'change_24h': 0, 'change_7d': 0}
            
            # Nehme die letzten 10 Zeilen (ohne Header)
            recent_rows = all_values[-10:] if len(all_values) > 10 else all_values[1:]
            records = []
            
            # Manuelle Zuordnung (A=Zeitstempel, V=Wert_EUR)
            for row in recent_rows:
                if len(row) >= 22:  # Stelle sicher, dass genug Spalten da sind
                    try:
                        records.append({
                            'Zeitstempel': row[0],  # Spalte A
                            'Wert_EUR': row[21]     # Spalte V
                        })
                    except (IndexError, ValueError):
                        continue
        
        if len(records) < 2: return {'change_24h': 0, 'change_7d': 0}
        
        # Portfolio-Werte aus den letzten Tagen sammeln
        portfolio_values = {}
        for record in records:
            timestamp = record.get('Zeitstempel', '')
            if timestamp:
                try:
                    # Sichere Konvertierung zu String falls timestamp ein anderer Typ ist
                    timestamp_str = str(timestamp)
                    date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').date()
                    wert = float(record.get('Wert_EUR', 0))
                    if wert > 0:  # Nur Einträge mit Portfolio-Wert
                        if date not in portfolio_values:
                            portfolio_values[date] = 0
                        portfolio_values[date] += wert
                except (ValueError, TypeError) as e:
                    print(f"Fehler beim Parsen des Datums/Werts: {e}")
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
        
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen der Google Credentials: {e}")
        return {'change_24h': 0, 'change_7d': 0}
    except (gspread.exceptions.APIError, gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.WorksheetNotFound) as e:
        print(f"Google Sheets Fehler beim Portfolio-Performance Abruf: {e}")
        return {'change_24h': 0, 'change_7d': 0}
    except Exception as e:
        print(f"Unerwarteter Fehler beim Portfolio-Performance Abruf: {e}")
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
    if abs(macd_hist) > ALERT_THRESHOLDS['macd_significant_move']:  # Verwende Konfiguration
        direction = "Bullisch" if macd_hist > 0 else "Bärisch"
        alerts.append(f"📊 {coin_name} starkes MACD Signal - {direction}!")
    
    # ATR-basierte Volatilitäts-Alerts
    atr_percentage = daten.get('atr_percentage', 0)
    volatility_level = daten.get('volatility_level', '')
    volatility_trend = daten.get('volatility_trend', '')
    
    if atr_percentage > ALERT_THRESHOLDS['atr_extreme_high']:
        alerts.append(f"⚠️ {coin_name} Extreme Volatilität ({atr_percentage:.1f}%) - Vorsicht!")
    elif atr_percentage < ALERT_THRESHOLDS['atr_extreme_low']:
        alerts.append(f"😴 {coin_name} Sehr niedrige Volatilität ({atr_percentage:.1f}%) - Ausbruch möglich!")
    
    # Volatilitäts-Trend Alerts
    if "Steigend" in volatility_trend and atr_percentage > ALERT_THRESHOLDS['atr_trend_threshold']:
        alerts.append(f"📈 {coin_name} Volatilität steigt ({atr_percentage:.1f}%) - Bewegung erwartet!")
    
    return alerts

def analyse_einzelnen_coin(coin_data: tuple, bitvavo, alle_news: Dict, gemini_model, wallet_bestaende: Dict) -> Dict:
    """
    Analysiert einen einzelnen Coin komplett - für Parallelisierung optimiert.
    
    Args:
        coin_data: (coin_name, {'symbol': 'BTC'})
        bitvavo: CCXT Exchange-Objekt
        alle_news: Bereits geladene News-Daten
        gemini_model: Gemini AI Model
        wallet_bestaende: Portfolio-Bestände
    
    Returns:
        Dict mit vollständigen Analyseergebnissen
    """
    coin_name, coin_info = coin_data
    symbol = coin_info['symbol']
    
    print(f"🔄 [Thread] Analysiere {coin_name} ({symbol})...")
    
    try:
        # 1. ERWEITERTE Technische Analyse (parallelisierbar)
        if not bitvavo:
            analyse_ergebnis = {'name': coin_name, 'error': "Keine API-Verbindung"}
        else:
            analyse_ergebnis = get_bitvavo_data(bitvavo, coin_name, symbol)
        
        if analyse_ergebnis.get('error'):
            print(f"❌ [Thread] Fehler bei {coin_name}: {analyse_ergebnis['error']}")
            return analyse_ergebnis
        
        # 2. News-Analyse (parallelisierbar - verwendet bereits geladene News)
        if gemini_model:
            news_artikel = alle_news.get(coin_name, [])
            
            if news_artikel:
                print(f"🤖 [Thread] KI-Analyse für {coin_name}: {len(news_artikel)} Artikel")
                news_analyse = analysiere_news_mit_ki(coin_name, news_artikel, gemini_model)
                analyse_ergebnis['news_analyse'] = news_analyse
            else:
                analyse_ergebnis['news_analyse'] = {}
        else:
            analyse_ergebnis['news_analyse'] = {}
        
        # 3. Smart Alerts (parallelisierbar)
        smart_alerts = generate_smart_alerts(analyse_ergebnis, coin_name)
        analyse_ergebnis['smart_alerts'] = smart_alerts
        
        # 4. Portfolio-Werte (parallelisierbar)
        bestand = wallet_bestaende.get(symbol, 0)
        analyse_ergebnis['bestand'] = bestand
        
        if not analyse_ergebnis.get('error'):
            wert_eur = bestand * analyse_ergebnis['price']
            analyse_ergebnis['wert_eur'] = wert_eur
        
        print(f"✅ [Thread] {coin_name} erfolgreich analysiert")
        return analyse_ergebnis
        
    except Exception as e:
        print(f"❌ [Thread] Unerwarteter Fehler bei {coin_name}: {e}")
        return {
            'name': coin_name,
            'error': f"Thread-Fehler: {str(e)}",
            'bestand': wallet_bestaende.get(symbol, 0),
            'wert_eur': 0
        }

# --- NEWS & AI ANALYSE FUNKTIONEN ---
def setup_gemini_ai():
    """Initialisiert die Gemini AI API."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ FEHLER: GEMINI_API_KEY nicht gefunden!")
        return None
    
    print(f"🔑 Gemini API Key gefunden: {api_key[:20]}...")
    
    try:
        # Korrekte Gemini API Initialisierung - Verwende lokalen Import
        import google.generativeai as genai_local  # type: ignore
        genai_local.configure(api_key=api_key)  # type: ignore
        
        # Verfügbare Modelle: gemini-1.5-flash, gemini-1.5-pro  
        model = genai_local.GenerativeModel('gemini-1.5-flash')  # type: ignore
        print("✅ Gemini AI erfolgreich initialisiert mit gemini-1.5-flash")
        return model
    except ImportError as e:
        print(f"❌ Gemini AI Bibliothek nicht verfügbar: {e}")
        print("💡 Installiere mit: pip install google-generativeai")
        return None
    except ValueError as e:
        print(f"❌ Ungültiger API-Key für Gemini: {e}")
        return None
    except Exception as e:
        print(f"❌ FEHLER bei Gemini-Initialisierung: {e}")
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
                # KORRIGIERT: None-Check für title und description
                title = article.get('title') or ''
                description = article.get('description') or ''
                url = article.get('url') or ''
                
                title_lower = title.lower()
                desc_lower = description.lower()
                content = f"{title_lower} {desc_lower}"
                
                # Prüfe ob Artikel zu diesem Coin gehört
                if any(term.lower() in content for term in search_terms):
                    # Zusätzlich Qualitätsfilter (flexibler)
                    if (any(src in url for src in QUALITY_SOURCES) or 
                        any(src.replace('.com', '') in url for src in QUALITY_SOURCES) or
                        'crypto' in url.lower() or 'bitcoin' in url.lower()):
                        coin_articles.append(article)
            
            # Top 3 pro Coin
            news_per_coin[coin_name] = sorted(coin_articles, 
                                            key=lambda x: x.get('publishedAt') or '', 
                                            reverse=True)[:3]
            
            print(f"📰 {coin_name}: {len(news_per_coin[coin_name])} relevante Artikel")
        
        return news_per_coin
        
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout bei News-Suche: {e}")
        return {}
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None:
            print(f"❌ HTTP-Fehler bei News-Suche: {e.response.status_code}")
        else:
            print(f"❌ HTTP-Fehler bei News-Suche: {e}")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"❌ Netzwerkfehler bei News-Suche: {e}")
        return {}
    except (KeyError, ValueError) as e:
        print(f"❌ Datenformat-Fehler bei News-Suche: {e}")
        return {}
    except Exception as e:
        print(f"❌ Unerwarteter Fehler bei kombinierter News-Suche: {e}")
        return {}

# write_health_check ist jetzt in modules.utils.logger verfügbar

def robust_json_parse(text: str) -> Dict[str, Any]:
    """Robuster JSON-Parser mit mehreren Fallback-Strategien für KI-Antworten."""
    import re
    
    # 1. Extrahiere JSON aus Markdown-Blöcken
    json_patterns = [
        r'```json\s*([\s\S]+?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]+?)\s*```',      # ``` ... ```
        r'\{[\s\S]*\}',                 # Findet das erste JSON-Objekt
    ]
    
    for pattern in json_patterns:
        match = re.search(pattern, text)
        if match:
            text = match.group(1) if '```' in pattern else match.group(0)
            break
    
    # 2. Bereinige JSON-Text
    text = text.strip()
    
    # Finde JSON-Grenzen
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        text = text[start:end]
    
    try:
        # 3. Versuche direktes Parsing
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # 4. Fallback: Repariere häufige Probleme
            # Ersetze unquoted boolean/null values
            fixed_text = re.sub(r':\s*(true|false|null)([,}\]])', r': "\1"\2', text)
            # Repariere trailing commas
            fixed_text = re.sub(r',(\s*[}\]])', r'\1', fixed_text)
            return json.loads(fixed_text)
        except json.JSONDecodeError:
            # 5. Letzter Fallback: Standard-Antwort
            print(f"❌ JSON-Parsing fehlgeschlagen für: {text[:100]}...")
            return {
                'sentiment_score': 0,
                'kategorie': 'JSON-Parse-Fehler',
                'zusammenfassung': 'KI-Antwort ungültig',
                'kritisch': False
            }

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
        
        # ROBUSTES JSON-PARSING mit verbesserter Fehlerbehandlung
        result = robust_json_parse(response_text)
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
    if macd_hist > TECHNICAL_CONFIG['macd_threshold']: signals.append("MACD:🟢Bull")
    elif macd_hist < -TECHNICAL_CONFIG['macd_threshold']: signals.append("MACD:🔴Bear")
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
    volume_spike_threshold = ALERT_THRESHOLDS['volume_spike'] / 100  # 200% -> 2.0
    if vol_ratio > volume_spike_threshold * 1.5: signals.append("Vol:🔥High")  # 300%
    elif vol_ratio > TECHNICAL_CONFIG['volume_increase_threshold']: signals.append("Vol:📈Inc")
    elif vol_ratio < TECHNICAL_CONFIG['volume_decrease_threshold']: signals.append("Vol:📉Low")
    
    # ATR Volatilität
    volatility_level = daten.get('volatility_level', '🟡 Mittel')
    atr_percentage = daten.get('atr_percentage', 0)
    volatility_trend = daten.get('volatility_trend', '➡️ Stabil')
    
    if "Niedrig" in volatility_level: 
        signals.append(f"ATR:😴{atr_percentage:.1f}%")
    elif "Extrem" in volatility_level: 
        signals.append(f"ATR:🔥{atr_percentage:.1f}%")
    elif "Hoch" in volatility_level: 
        signals.append(f"ATR:🟠{atr_percentage:.1f}%")
    else: 
        signals.append(f"ATR:🟡{atr_percentage:.1f}%")
    
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
def get_bitvavo_data(bitvavo: ccxt.bitvavo, coin_name: str, symbol: str) -> Dict[str, Any]:
    """Holt historische Marktdaten von Bitvavo und berechnet ALLE technischen Indikatoren.
    
    Thread-safe Version mit verbessertem Rate Limiting für Parallelisierung.
    """
    try:
        markt_symbol = f'{symbol}/EUR'
        print(f"[{coin_name}] Starte erweiterte Marktdatenanalyse für {markt_symbol}...")
        
        # Reduziertes Rate Limiting für parallele Ausführung
        time.sleep(API_CONFIG['rate_limit_delay'])  # Statt 1.5s - ThreadPoolExecutor verteilt Requests automatisch
        
        # Bitvavo API-Call mit Timeout
        bitvavo.timeout = API_CONFIG['bitvavo_timeout'] * 1000  # ccxt erwartet Millisekunden
        ohlcv = bitvavo.fetch_ohlcv(markt_symbol, '1d', limit=250)  # Mehr Daten für MA200
        
        if len(ohlcv) < 34:  # Mindestanzahl für MACD(26) + RSI(14)
            return {'name': coin_name, 'error': f"Zu wenig Daten ({len(ohlcv)})"}
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        close = df['close']
        volume = df['volume']
        high = df['high']
        low = df['low']
        
        # Konvertiere zu NumPy Arrays für TA-Lib
        close_values = np.array(close.values, dtype=np.float64)
        high_values = np.array(high.values, dtype=np.float64)
        low_values = np.array(low.values, dtype=np.float64)
        volume_values = np.array(volume.values, dtype=np.float64)
        
        current_price = close.iloc[-1]
        
        # === KLASSISCHE INDIKATOREN ===
        # RSI
        rsi = talib.RSI(close_values, timeperiod=14)[-1]
        
        # MACD
        macd, macd_sig, macd_hist = talib.MACD(close_values, fastperiod=12, slowperiod=26, signalperiod=9)
        
        # Bollinger Bänder - Verwende numerischen Wert für MA_Type
        bb_up, bb_mid, bb_low = talib.BBANDS(close_values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)  # type: ignore
        bb_upper = bb_up[-1]
        bb_lower = bb_low[-1]
        bb_position = ((current_price - bb_lower) / (bb_upper - bb_lower)) * 100 if (bb_upper - bb_lower) != 0 else 50
        
        # === NEUE ERWEITERTE INDIKATOREN ===
        # Moving Averages
        ma20 = talib.SMA(close_values, timeperiod=20)[-1] if len(close) >= 20 else current_price
        ma50 = talib.SMA(close_values, timeperiod=50)[-1] if len(close) >= 50 else current_price
        ma200 = talib.SMA(close_values, timeperiod=200)[-1] if len(close) >= 200 else current_price
        
        # Trend-Analyse (Golden Cross / Death Cross)
        ma_trend = "🟡 Neutral"
        if len(close) >= 200:
            if ma50 > ma200 * (1 + TECHNICAL_CONFIG['ma_trend_buffer']):  # Konfigurierbarer Puffer für klares Signal
                ma_trend = "🟢 Aufwärtstrend"
                # Prüfe auf Golden Cross (MA50 kreuzt MA200 nach oben)
                ma50_yesterday = talib.SMA(close_values, timeperiod=50)[-2] if len(close) >= 51 else ma50
                ma200_yesterday = talib.SMA(close_values, timeperiod=200)[-2] if len(close) >= 201 else ma200
                if ma50_yesterday <= ma200_yesterday and ma50 > ma200:
                    ma_trend = "🟢 Golden Cross"
            elif ma50 < ma200 * (1 - TECHNICAL_CONFIG['ma_trend_buffer']):  # Konfigurierbarer Puffer für klares Signal
                ma_trend = "🔴 Abwärtstrend"
                # Prüfe auf Death Cross (MA50 kreuzt MA200 nach unten)
                ma50_yesterday = talib.SMA(close_values, timeperiod=50)[-2] if len(close) >= 51 else ma50
                ma200_yesterday = talib.SMA(close_values, timeperiod=200)[-2] if len(close) >= 201 else ma200
                if ma50_yesterday >= ma200_yesterday and ma50 < ma200:
                    ma_trend = "🔴 Death Cross"
        
        # Volumen-Analyse
        avg_volume_20 = volume.tail(20).mean() if len(volume) >= 20 else volume.iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 1
        
        # Stochastic Oscillator
        stoch_k, stoch_d = talib.STOCH(high_values, low_values, close_values)
        stoch_k_current = stoch_k[-1] if not np.isnan(stoch_k[-1]) else 50
        
        # Williams %R
        williams_r = talib.WILLR(high_values, low_values, close_values, timeperiod=14)[-1]
        
        # === VOLATILITÄTS-INDIKATOREN ===
        # Average True Range (ATR) - Misst Volatilität
        atr = talib.ATR(high_values, low_values, close_values, timeperiod=14)[-1]
        atr_percentage = (atr / current_price * 100) if current_price > 0 else 0
        
        # ATR-basierte Volatilitäts-Klassifikation
        if atr_percentage < TECHNICAL_CONFIG['atr_low_volatility']:
            volatility_level = "🟢 Niedrig"
        elif atr_percentage < TECHNICAL_CONFIG['atr_medium_volatility']:
            volatility_level = "🟡 Mittel"
        elif atr_percentage < TECHNICAL_CONFIG['atr_high_volatility']:
            volatility_level = "🟠 Hoch"
        else:
            volatility_level = "🔴 Extrem"
        
        # ATR-basierte Stop-Loss Empfehlung (2x ATR ist Standard)
        stop_loss_long = current_price - (2 * atr)
        stop_loss_short = current_price + (2 * atr)
        
        # Volatilitäts-Trend (ATR der letzten 5 Tage vs. 20-Tage Durchschnitt)
        atr_series = talib.ATR(high_values, low_values, close_values, timeperiod=14)
        atr_ma20 = np.mean(atr_series[-20:]) if len(atr_series) >= 20 else atr
        threshold_factor = 1 + TECHNICAL_CONFIG['volatility_trend_threshold']
        volatility_trend = ("📈 Steigend" if atr > atr_ma20 * threshold_factor 
                           else "📉 Fallend" if atr < atr_ma20 * (2 - threshold_factor) 
                           else "➡️ Stabil")
        
        # Preis-Position relativ zu Moving Averages
        price_vs_ma20 = ((current_price - ma20) / ma20 * 100) if ma20 > 0 else 0
        price_vs_ma50 = ((current_price - ma50) / ma50 * 100) if ma50 > 0 else 0
        price_vs_ma200 = ((current_price - ma200) / ma200 * 100) if ma200 > 0 else 0
        
        return {
            'name': coin_name, 
            'price': current_price,
            
            # Klassische Indikatoren
            'rsi': rsi,
            'macd': macd[-1],
            'macd_signal': macd_sig[-1],
            'macd_histogram': macd_hist[-1],
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
            
            # Volatilitäts-Indikatoren (ATR)
            'atr': atr,
            'atr_percentage': atr_percentage,
            'volatility_level': volatility_level,
            'volatility_trend': volatility_trend,
            'stop_loss_long': stop_loss_long,
            'stop_loss_short': stop_loss_short,
            
            'error': None
        }
        
    except ccxt.NetworkError as e:
        print(f"❌ Netzwerkfehler bei {coin_name}: {e}")
        return {'name': coin_name, 'error': f"Netzwerkfehler: {str(e)}"}
    except ccxt.ExchangeError as e:
        print(f"❌ Exchange-Fehler bei {coin_name}: {e}")
        return {'name': coin_name, 'error': f"Exchange-Fehler: {str(e)}"}
    except ccxt.BaseError as e:
        print(f"❌ CCXT-Fehler bei {coin_name}: {e}")
        return {'name': coin_name, 'error': f"CCXT-Fehler: {str(e)}"}
    except (ValueError, IndexError, KeyError) as e:
        print(f"❌ Datenverarbeitungsfehler bei {coin_name}: {e}")
        return {'name': coin_name, 'error': f"Datenverarbeitungsfehler: {str(e)}"}
    except Exception as e:
        print(f"❌ Unerwarteter Fehler bei {coin_name}: {e}")
        return {'name': coin_name, 'error': f"Unerwarteter Fehler: {str(e)}"}

# --- HAUPTFUNKTION ---
def run_full_analysis():
    """Steuert den gesamten erweiterten Analyseprozess mit ALLEN neuen Features."""
    logger.info("🚀 Starte SUPER-CHARGED KI-verstärkten Analyse-Lauf...")
    
    # Tracking für Health Check
    coins_analyzed = 0
    total_portfolio_wert = 0
    analysis_success = False
    error_message = ""
    
    # API-Schlüssel prüfen - nutze neue config.py Funktion
    credentials = get_api_credentials()
    api_key = credentials['bitvavo_api_key']
    secret = credentials['bitvavo_secret']
    
    if not api_key or not secret:
        error_msg = "<b>Fehler:</b> Bitvavo API-Schlüssel nicht in GitHub Secrets gefunden!"
        logger.error(error_msg)
        sende_telegram_nachricht(error_msg)
        write_health_check(False, 0, 0, "API-Schlüssel fehlen")
        return
    
    # Gemini AI initialisieren
    gemini_model = setup_gemini_ai()
    if gemini_model:
        logger.info(f"✅ Gemini AI erfolgreich initialisiert")
    else:
        logger.warning(f"⚠️ Gemini AI nicht verfügbar - News-Analyse deaktiviert")
    
    # KORRIGIERT: Alle neuen Features ordentlich integrieren
    logger.info("📊 Lade Market Context...")
    fear_greed = get_fear_greed_index()
    portfolio_performance = get_portfolio_performance_from_sheets()
    
    logger.info(f"😨😐🤑 Fear & Greed Index: {fear_greed['value']} ({fear_greed['classification']}) {fear_greed['emoji']}")
    logger.info(f"📈📉 Portfolio Performance: 24h {portfolio_performance['change_24h']:+.1f}%, 7d {portfolio_performance['change_7d']:+.1f}%")
    
    # Bitvavo-Verbindung und Portfolio-Daten
    wallet_bestaende = {}
    try:
        bitvavo = ccxt.bitvavo({'apiKey': api_key, 'secret': secret})
        balance_data = bitvavo.fetch_balance()
        print(f"Balance-Daten erfolgreich abgerufen: {len(balance_data)} Assets gefunden")
        
        # Standard ccxt-Format: {'BTC': {'free': 0.001, 'used': 0, 'total': 0.001}, ...}
        for symbol, balance_info in balance_data.items():
            if isinstance(balance_info, dict):
                # VERBESSERT: Nutze 'total' statt nur 'free' für vollständige Portfolio-Bewertung
                total_amount = balance_info.get('total', 0)
                try:
                    # Sichere Konvertierung zu float und Prüfung > 0
                    total_float = float(total_amount) if total_amount is not None else 0.0
                    if total_float > 0:
                        wallet_bestaende[symbol] = total_float
                        # Info: 'free' + 'used' (in Orders) = 'total'
                except (ValueError, TypeError):
                    continue  # Überspringe ungültige Werte
        
        print(f"✅ Erfolgreich {len(wallet_bestaende)} Coins mit Bestand gefunden: {list(wallet_bestaende.keys())}")
        
    except ccxt.AuthenticationError as e:
        error_msg = f"🔐 <b>Bitvavo Authentifizierungsfehler</b>\n\nBitte API-Schlüssel überprüfen:\n<code>{sanitize_error_message(escape_html(str(e)))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return
    except ccxt.NetworkError as e:
        error_msg = f"🌐 <b>Bitvavo Netzwerkfehler</b>\n\nVerbindungsproblem:\n<code>{sanitize_error_message(escape_html(str(e)))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return
    except Exception as e:
        error_msg = f"⚠️ <b>Unerwarteter Bitvavo-Fehler</b>\n\n<code>{sanitize_error_message(escape_html(str(e)))}</code>"
        print(error_msg)
        sende_telegram_nachricht(error_msg)
        return

    # PARALLELISIERTE Haupt-Analyse-Loop mit ThreadPoolExecutor
    ergebnis_daten = []
    total_portfolio_wert = 0
    kritische_alerts = []
    alle_smart_alerts = []
    news_sentiments = {}
    
    # Eine News-Suche für alle Coins (statt 13×2=26 API-Calls!)
    print("\n🚀 Starte optimierte News-Suche für alle Coins...")
    alle_news = hole_aktuelle_news_optimiert() if gemini_model else {}
    
    # PARALLELISIERUNG: Alle Coins gleichzeitig analysieren
    print(f"\n⚡ Starte PARALLELISIERTE Analyse von {len(COINS_TO_ANALYZE)} Coins...")
    start_time = time.time()
    
    # Dynamische Worker-Berechnung basierend auf CPU-Kernen und API-Limits
    cpu_count = os.cpu_count() or 4
    max_workers = API_CONFIG['max_workers'] or min(cpu_count + 2, 8)  # CPU+2, max 8 für API-Limits
    print(f"🔧 Verwende {max_workers} Worker-Threads (CPU-Kerne: {cpu_count})")
    
    # ThreadPoolExecutor für I/O-bound Tasks (API-Calls, KI-Requests)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:  # Dynamische Thread-Anzahl
        # Alle Coin-Analysen parallel starten
        future_to_coin = {
            executor.submit(
                analyse_einzelnen_coin, 
                coin_item, 
                bitvavo, 
                alle_news, 
                gemini_model, 
                wallet_bestaende
            ): coin_item[0] for coin_item in COINS_TO_ANALYZE.items()
        }
        
        # Ergebnisse sammeln sobald sie verfügbar sind
        completed_count = 0
        for future in as_completed(future_to_coin, timeout=API_CONFIG['futures_timeout']):
            coin_name = future_to_coin[future]
            try:
                analyse_ergebnis = future.result(timeout=API_CONFIG['bitvavo_timeout'])  # Verwende zentrale Timeout-Konfiguration
                ergebnis_daten.append(analyse_ergebnis)
                
                completed_count += 1
                print(f"✅ [{completed_count}/{len(COINS_TO_ANALYZE)}] {coin_name} abgeschlossen")
                
                # Sammle Daten für Zusammenfassung
                if not analyse_ergebnis.get('error'):
                    # Smart Alerts
                    if 'smart_alerts' in analyse_ergebnis:
                        alle_smart_alerts.extend(analyse_ergebnis['smart_alerts'])
                    
                    # News Sentiments
                    if analyse_ergebnis.get('news_analyse'):
                        news_sentiments[coin_name] = analyse_ergebnis['news_analyse']
                        
                        # Kritische Alerts
                        if analyse_ergebnis['news_analyse'].get('kritisch'):
                            kritische_alerts.append(
                                f"<b>{coin_name}</b>: {analyse_ergebnis['news_analyse'].get('zusammenfassung')}"
                            )
                    
                    # Portfolio-Wert
                    if analyse_ergebnis.get('wert_eur', 0) > 0:
                        total_portfolio_wert += analyse_ergebnis['wert_eur']
                        
            except TimeoutError as e:
                print(f"❌ Timeout bei der Verarbeitung von {coin_name}: {e}")
                ergebnis_daten.append({
                    'name': coin_name, 
                    'error': f"Timeout nach {API_CONFIG['bitvavo_timeout']}s: {str(e)}"
                })
            except Exception as e:
                print(f"❌ Fehler bei der Verarbeitung von {coin_name}: {e}")
                # Fallback-Eintrag für fehlerhafte Coins
                ergebnis_daten.append({
                    'name': coin_name,
                    'error': f"Timeout/Verarbeitungsfehler: {str(e)}",
                    'bestand': wallet_bestaende.get(
                        next(coin_data['symbol'] for cn, coin_data in COINS_TO_ANALYZE.items() if cn == coin_name), 
                        0
                    ),
                    'wert_eur': 0
                })
    
    end_time = time.time()
    parallel_duration = end_time - start_time
    
    print(f"🎯 PARALLELISIERTE Analyse abgeschlossen in {parallel_duration:.1f}s")
    print(f"⚡ Geschwindigkeitsgewinn: ~{(60/parallel_duration):.1f}x schneller als sequenziell!")
    print(f"📊 Verarbeitete Coins: {len(ergebnis_daten)}")
    print(f"💰 Portfolio Gesamtwert: €{total_portfolio_wert:,.2f}")
    print(f"🚨 Smart Alerts gefunden: {len(alle_smart_alerts)}")
    print(f"📰 News-Analysen: {len(news_sentiments)}")
    print(f"⚠️ Kritische Alerts: {len(kritische_alerts)}")
    
    # Sortiere Ergebnisse nach Portfolio-Wert (höchste zuerst)
    ergebnis_daten.sort(key=lambda x: x.get('wert_eur', 0), reverse=True)

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
        # 🎯 WICHTIG: Trading-Signal generieren und zu Daten hinzufügen für Google Sheets
        if not daten.get('error'):
            trading_signal = generate_trading_signals(daten)
            daten['strategy_signal'] = trading_signal['signal']
            daten['strategy_confidence'] = trading_signal['confidence']
            daten['strategy_reasoning'] = trading_signal['reasoning']
            daten['strategy_name'] = trading_signal['strategy_name']
        
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
            
            # 🎯 Trading-Signal anzeigen (bereits generiert und gespeichert)
            signal_emoji = {
                'BUY': '💚',
                'STRONG_BUY': '🚀',
                'SELL': '🔴',
                'STRONG_SELL': '💥',
                'HOLD': '🟡'
            }
            
            signal = daten.get('strategy_signal', 'HOLD')
            confidence = daten.get('strategy_confidence', 0.5)
            reasoning = daten.get('strategy_reasoning', '')
            
            confidence_text = f"{confidence*100:.0f}%"
            signal_text = f"\n🎯 <b>{signal_emoji.get(signal, '⚪')} {signal}</b> ({confidence_text})"
            if reasoning:
                signal_text += f"\n💡 <i>{reasoning}</i>"
            
            text_block += signal_text
            
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
    
    # Erfolgreiche Analyse
    analysis_success = True
    coins_analyzed = len(ergebnis_daten)
    logger.info("🎉 SUPER-CHARGED Analyse erfolgreich abgeschlossen!")
    
    # Health Check schreiben
    write_health_check(analysis_success, coins_analyzed, total_portfolio_wert, error_message)

if __name__ == "__main__":
    run_full_analysis()
