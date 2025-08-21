"""
Zentrale Konfigurationsdatei für die Krypto-Analyse- und Simulations-Plattform.

Diese Datei enthält alle einstellbaren Parameter für:
- API-Konfigurationen
- Technische Analyse-Parameter  
- Trading-Strategien
- Simulation-Einstellungen
- Performance-Metriken
"""

import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# === API KONFIGURATION ===
API_CONFIG = {
    'bitvavo_timeout': 30,      # Timeout für Bitvavo API-Calls in Sekunden
    'telegram_timeout': 10,     # Timeout für Telegram API-Calls
    'news_api_timeout': 15,     # Timeout für News API-Calls
    'gemini_timeout': 20,       # Timeout für Google Gemini API-Calls
    'gsheets_timeout': 25,      # Timeout für Google Sheets API-Calls
    'futures_timeout': 300,     # Timeout für ThreadPoolExecutor Futures (5 Min)
    'max_workers': None,        # Dynamisch berechnet basierend auf CPU-Kernen
    'retry_attempts': 3,        # Anzahl Wiederholungsversuche bei API-Fehlern
    'rate_limit_delay': 0.2,    # Sekunden zwischen API-Calls für Rate Limiting
}

# === COINS ZUR ANALYSE ===
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

# === NEWS & AI KONFIGURATION ===
QUALITY_SOURCES = [
    'coindesk.com', 'cointelegraph.com', 'reuters.com', 'bloomberg.com', 'cnbc.com', 
    'forbes.com', 'wsj.com', 'ft.com', 'coinbase.com', 'crypto.news', 'decrypt.co',
    'theblock.co', 'cryptoslate.com', 'bitcoin.com', 'coingecko.com'
]

CRITICAL_KEYWORDS = [
    'SEC', 'lawsuit', 'ban', 'banned', 'regulation', 'hack', 'hacked', 
    'fraud', 'investigation', 'seized', 'arrest'
]

# === TECHNISCHE ANALYSE PARAMETER ===
TECHNICAL_CONFIG = {
    'ma_trend_buffer': 0.02,           # 2% Puffer für MA-Trend-Erkennung
    'macd_threshold': 0.0001,          # MACD Histogram Schwellwert für Signale
    'volume_increase_threshold': 1.5,   # Faktor für erhöhtes Volumen
    'volume_decrease_threshold': 0.5,   # Faktor für verringertes Volumen
    'atr_low_volatility': 1.5,         # ATR % Schwelle für niedrige Volatilität
    'atr_medium_volatility': 3.0,      # ATR % Schwelle für mittlere Volatilität
    'atr_high_volatility': 5.0,        # ATR % Schwelle für hohe Volatilität
    'volatility_trend_threshold': 0.1,  # 10% für Volatilitäts-Trend-Erkennung
    'rsi_period': 14,                  # RSI Berechnungsperiode
    'macd_fast': 12,                   # MACD Fast EMA
    'macd_slow': 26,                   # MACD Slow EMA
    'macd_signal': 9,                  # MACD Signal Line
    'bb_period': 20,                   # Bollinger Bands Periode
    'bb_std': 2,                       # Bollinger Bands Standardabweichungen
}

# === ALERT SCHWELLENWERTE ===
ALERT_THRESHOLDS = {
    'breakout_percentage': 2.0,        # % über Bollinger Band für Breakout
    'rsi_oversold': 25,               # RSI unter diesem Wert = Alert
    'rsi_overbought': 75,             # RSI über diesem Wert = Alert
    'volume_spike': 200,              # % Volumen-Anstieg für Alert
    'macd_significant_move': 0.001,   # MACD Bewegung für Alert
    'atr_extreme_high': 5.0,          # ATR % für extreme Volatilität
    'atr_extreme_low': 1.0,           # ATR % für sehr niedrige Volatilität
    'atr_trend_threshold': 3.0,       # ATR % ab dem Trend-Alerts ausgelöst werden
}

# === NEUE SIMULATION KONFIGURATION ===
SIMULATION_CONFIG = {
    'initial_balance': 10000.0,       # Startkapital für Simulation (EUR)
    'transaction_fee': 0.0025,        # 0.25% Transaktionsgebühr
    'slippage': 0.001,                # 0.1% Slippage
    'max_position_size': 0.2,         # Max 20% des Portfolios pro Position
    'min_trade_amount': 10.0,         # Mindest-Handelsbetrag (EUR)
    'rebalance_threshold': 0.05,      # 5% Abweichung für Rebalancing
    'backtest_days': 90,              # Tage für Backtesting
    'performance_benchmark': 'BTC',    # Benchmark für Performance-Vergleich
}

# === TRADING STRATEGIEN ===
@dataclass
class StrategyConfig:
    """Konfiguration für eine Trading-Strategie."""
    name: str
    enabled: bool
    parameters: Dict[str, Any]
    risk_level: str  # 'conservative', 'moderate', 'aggressive'
    max_positions: int
    description: str

STRATEGIES = {
    'conservative_trend': StrategyConfig(
        name='Conservative Trend Following',
        enabled=True,
        parameters={
            'ma_short_period': 50,
            'ma_long_period': 200,
            'rsi_oversold': 20,
            'rsi_overbought': 80,
            'volume_threshold': 1.2,
            'stop_loss_pct': 0.05,      # 5% Stop Loss
            'take_profit_pct': 0.15,    # 15% Take Profit
            'position_size': 0.1,       # 10% des Portfolios
        },
        risk_level='conservative',
        max_positions=3,
        description='Langfristige Trendfolge mit konservativen Parametern'
    ),
    
    'moderate_momentum': StrategyConfig(
        name='Moderate Momentum',
        enabled=True,
        parameters={
            'ma_short_period': 20,
            'ma_long_period': 50,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_threshold': 0.0001,
            'volume_threshold': 1.5,
            'stop_loss_pct': 0.08,      # 8% Stop Loss
            'take_profit_pct': 0.20,    # 20% Take Profit
            'position_size': 0.15,      # 15% des Portfolios
        },
        risk_level='moderate',
        max_positions=5,
        description='Mittelfristige Momentum-Strategie mit ausgewogenen Parametern'
    ),
    
    'aggressive_scalping': StrategyConfig(
        name='Aggressive Scalping',
        enabled=False,  # Standardmäßig deaktiviert
        parameters={
            'ma_short_period': 5,
            'ma_long_period': 20,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'bb_squeeze_threshold': 0.1,
            'volume_threshold': 2.0,
            'stop_loss_pct': 0.03,      # 3% Stop Loss
            'take_profit_pct': 0.06,    # 6% Take Profit
            'position_size': 0.25,      # 25% des Portfolios
        },
        risk_level='aggressive',
        max_positions=8,
        description='Kurzfristige Scalping-Strategie mit hohem Risiko'
    ),
    
    'manual_reference': StrategyConfig(
        name='Manual Trading Reference',
        enabled=True,
        parameters={
            'track_only': True,  # Nur Tracking, keine automatischen Trades
        },
        risk_level='user_defined',
        max_positions=999,  # Unbegrenzt
        description='Referenz-Portfolio basierend auf manuellen Trades des Nutzers'
    )
}

# === PERFORMANCE METRIKEN ===
PERFORMANCE_CONFIG = {
    'benchmark_symbols': ['BTC', 'ETH'],  # Vergleichs-Assets
    'risk_free_rate': 0.02,              # 2% risikofreier Zinssatz für Sharpe Ratio
    'confidence_level': 0.95,            # Konfidenzniveau für VaR
    'rolling_window': 30,                # Tage für rollende Berechnungen
    'min_trades_for_stats': 10,          # Mindestanzahl Trades für Statistiken
}

# === UMGEBUNGSVARIABLEN ===
def get_api_credentials() -> Dict[str, Optional[str]]:
    """Holt API-Credentials aus Umgebungsvariablen."""
    return {
        'bitvavo_api_key': os.getenv('BITVAVO_API_KEY'),
        'bitvavo_secret': os.getenv('BITVAVO_API_SECRET'),
        'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
        'news_api_key': os.getenv('NEWS_API_KEY'),
        'gemini_api_key': os.getenv('GEMINI_API_KEY'),
        'google_credentials': os.getenv('GOOGLE_CREDENTIALS'),
    }

# === VALIDIERUNG ===
def validate_config() -> List[str]:
    """Validiert die Konfiguration und gibt Warnungen zurück."""
    warnings = []
    
    # API-Keys prüfen
    credentials = get_api_credentials()
    required_keys = ['bitvavo_api_key', 'bitvavo_secret']
    
    for key in required_keys:
        if not credentials.get(key):
            warnings.append(f"CRITICAL: {key} nicht in Umgebungsvariablen gefunden!")
    
    # Strategien validieren
    enabled_strategies = [s for s in STRATEGIES.values() if s.enabled]
    if not enabled_strategies:
        warnings.append("WARNING: Keine Strategien aktiviert!")
    
    # Parameter-Bereiche prüfen
    if SIMULATION_CONFIG['max_position_size'] > 1.0:
        warnings.append("WARNING: max_position_size > 100% ist riskant!")
    
    if SIMULATION_CONFIG['transaction_fee'] < 0:
        warnings.append("ERROR: Negative Transaktionsgebühren nicht möglich!")
    
    return warnings

# === PORTFOLIO HISTORY ===
PORTFOLIO_HISTORY_DAYS = 7  # Letzte 7 Tage für Performance-Vergleich

# === EXPORTIERE HAUPTKONFIGURATIONEN ===
__all__ = [
    'API_CONFIG', 'COINS_TO_ANALYZE', 'COIN_SEARCH_TERMS',
    'QUALITY_SOURCES', 'CRITICAL_KEYWORDS', 'TECHNICAL_CONFIG',
    'ALERT_THRESHOLDS', 'SIMULATION_CONFIG', 'STRATEGIES',
    'PERFORMANCE_CONFIG', 'get_api_credentials', 'validate_config'
]
