"""
Zentrale Datenmodelle und Type Definitions für die Krypto-Analyse-Plattform.

Diese Datei definiert alle Datenstrukturen, die zwischen den Modulen ausgetauscht werden.
Dadurch entstehen klare Interfaces und bessere Wartbarkeit.
"""

from typing import Dict, List, Any, Optional, TypedDict, Union, Protocol
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# === ENUMS ===
class TradingSignal(Enum):
    """Handelssignale für Strategieentscheidungen."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class VolatilityLevel(Enum):
    """Volatilitätsstufen basierend auf ATR."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

class TrendDirection(Enum):
    """Trendrichtungen für MA-Analyse."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    GOLDEN_CROSS = "GOLDEN_CROSS"
    DEATH_CROSS = "DEATH_CROSS"

# === CORE DATA MODELS ===
@dataclass
class MarketData:
    """Grundlegende Marktdaten für einen Coin."""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    high_24h: float
    low_24h: float
    change_24h: float

@dataclass
class TechnicalIndicators:
    """Sammlung aller technischen Indikatoren."""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    ma20: float
    ma50: float
    ma200: float
    bb_upper: float
    bb_lower: float
    bb_position: float
    atr: float
    atr_percentage: float
    stoch_k: float
    williams_r: float
    volume_ratio: float

@dataclass
class NewsAnalysis:
    """Ergebnis der KI-basierten News-Analyse."""
    sentiment_score: int  # -10 bis +10
    category: str
    summary: str
    is_critical: bool
    confidence: float  # 0.0 bis 1.0
    articles_count: int

@dataclass
class TradingDecision:
    """Handelsentscheidung einer Strategie."""
    signal: TradingSignal
    confidence: float
    reasoning: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: float  # Anteil des Portfolios (0.0 bis 1.0)

@dataclass
class PortfolioPosition:
    """Eine Position im Portfolio."""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: datetime
    strategy_name: str

@dataclass
class PerformanceMetrics:
    """Performance-Kennzahlen eines Portfolios."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float

# === STRATEGY INTERFACES ===
class Strategy(Protocol):
    """Interface für alle Trading-Strategien."""
    
    def get_name(self) -> str:
        """Gibt den Namen der Strategie zurück."""
        ...
    
    def analyze(self, market_data: MarketData, indicators: TechnicalIndicators, 
               news: Optional[NewsAnalysis]) -> TradingDecision:
        """Analysiert die Daten und gibt eine Handelsentscheidung zurück."""
        ...
    
    def get_parameters(self) -> Dict[str, Any]:
        """Gibt die aktuellen Strategie-Parameter zurück."""
        ...

class DataProvider(Protocol):
    """Interface für Datenquellen."""
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Holt aktuelle Marktdaten für ein Symbol."""
        ...
    
    def get_historical_data(self, symbol: str, days: int) -> List[MarketData]:
        """Holt historische Daten für technische Analyse."""
        ...

class PortfolioManager(Protocol):
    """Interface für Portfolio-Management."""
    
    def get_positions(self) -> List[PortfolioPosition]:
        """Gibt alle aktuellen Positionen zurück."""
        ...
    
    def execute_trade(self, symbol: str, signal: TradingSignal, 
                     quantity: float) -> bool:
        """Führt einen Trade aus (virtuell oder real)."""
        ...
    
    def get_performance(self) -> PerformanceMetrics:
        """Berechnet aktuelle Performance-Kennzahlen."""
        ...

# === LEGACY COMPATIBILITY ===
# Für Übergangszeit - alte TypedDict-Definitionen
class CoinAnalysisResult(TypedDict, total=False):
    """Legacy-Format für Rückwärtskompatibilität."""
    name: str
    symbol: Optional[str]
    price: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bb_position: float
    bb_upper: float
    bb_lower: float
    ma20: float
    ma50: float
    ma200: float
    ma_trend: str
    price_vs_ma20: float
    price_vs_ma50: float
    price_vs_ma200: float
    volume_ratio: float
    stoch_k: float
    williams_r: float
    atr: float
    atr_percentage: float
    volatility_level: str
    volatility_trend: str
    stop_loss_long: float
    stop_loss_short: float
    news_analyse: Dict[str, Any]
    smart_alerts: List[str]
    bestand: float
    wert_eur: float
    error: Optional[str]

# === CONVERSION UTILITIES ===
def legacy_to_new_format(legacy_data: CoinAnalysisResult) -> tuple[MarketData, TechnicalIndicators, Optional[NewsAnalysis]]:
    """Konvertiert Legacy-Format in neue Datenmodelle."""
    error = legacy_data.get('error')
    if error:
        raise ValueError(f"Cannot convert error result: {error}")
    
    market_data = MarketData(
        symbol=legacy_data.get('symbol') or '',
        price=legacy_data.get('price', 0.0),
        volume=0.0,  # Not available in legacy format
        timestamp=datetime.now(),
        high_24h=0.0,  # Not available in legacy format
        low_24h=0.0,   # Not available in legacy format
        change_24h=0.0  # Not available in legacy format
    )
    
    indicators = TechnicalIndicators(
        rsi=legacy_data.get('rsi', 50.0),
        macd=legacy_data.get('macd', 0.0),
        macd_signal=legacy_data.get('macd_signal', 0.0),
        macd_histogram=legacy_data.get('macd_histogram', 0.0),
        ma20=legacy_data.get('ma20', 0.0),
        ma50=legacy_data.get('ma50', 0.0),
        ma200=legacy_data.get('ma200', 0.0),
        bb_upper=legacy_data.get('bb_upper', 0.0),
        bb_lower=legacy_data.get('bb_lower', 0.0),
        bb_position=legacy_data.get('bb_position', 50.0),
        atr=legacy_data.get('atr', 0.0),
        atr_percentage=legacy_data.get('atr_percentage', 0.0),
        stoch_k=legacy_data.get('stoch_k', 50.0),
        williams_r=legacy_data.get('williams_r', -50.0),
        volume_ratio=legacy_data.get('volume_ratio', 1.0)
    )
    
    news_data = legacy_data.get('news_analyse')
    news_analysis = None
    if news_data:
        news_analysis = NewsAnalysis(
            sentiment_score=news_data.get('sentiment_score', 0),
            category=news_data.get('kategorie', 'Other'),
            summary=news_data.get('zusammenfassung', ''),
            is_critical=news_data.get('kritisch', False),
            confidence=0.8,  # Default confidence
            articles_count=1  # Default
        )
    
    return market_data, indicators, news_analysis
