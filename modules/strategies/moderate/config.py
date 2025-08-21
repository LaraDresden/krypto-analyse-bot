"""
Moderate Strategy Configuration.

Konfiguration für moderate Momentum-basierte Strategien mit:
- MACD-basierte Signalgenerierung
- Bollinger Band Breakout-Erkennung
- Mittleres Risiko-Management
- Adaptive Volatilitäts-Anpassung
"""

from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ModerateConfig:
    """Konfiguration für moderate Momentum-Strategien."""
    
    # Position Sizing
    max_position_size: float = 0.08  # 8% des Portfolios (höher als conservative 5%)
    min_position_size: float = 0.02  # 2% minimum
    
    # MACD Parameters
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    macd_threshold: float = 0.0001  # Minimum MACD histogram für Signal
    
    # Bollinger Band Parameters
    bb_period: int = 20
    bb_deviation: float = 2.0
    bb_breakout_threshold: float = 80.0  # Position % für Breakout (80% = near upper band)
    bb_oversold_threshold: float = 20.0  # Position % für Oversold (20% = near lower band)
    
    # RSI Parameters
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    rsi_neutral_upper: float = 60.0
    rsi_neutral_lower: float = 40.0
    
    # Risk Management
    stop_loss_atr_multiplier: float = 1.5  # Enger als conservative (2.0)
    take_profit_ratio: float = 2.5  # Risk/Reward ratio
    trailing_stop_enabled: bool = True
    trailing_stop_distance: float = 1.0  # ATR multiplier for trailing stop
    
    # Volatility Management
    max_atr_percentage: float = 4.0  # Höher als conservative (3.0%)
    min_atr_percentage: float = 0.5  # Minimum volatility for entry
    
    # Volume Confirmation
    volume_confirmation_enabled: bool = True
    min_volume_ratio: float = 1.2  # 20% über Durchschnitt
    volume_spike_threshold: float = 2.0  # 200% spike detection
    
    # News Sentiment
    min_news_sentiment: int = -2  # Weniger streng als conservative (-3)
    critical_news_block: bool = True
    
    # Confidence Thresholds
    min_confidence_buy: float = 0.65
    min_confidence_sell: float = 0.60
    
    # Multi-timeframe Analysis
    enable_trend_filter: bool = True
    trend_ma_period: int = 50  # MA50 für Trend-Filter
    
    # Position Management
    partial_profit_levels: Optional[List[float]] = None  # [50%, 75%] profit taking levels
    scale_in_enabled: bool = True  # Erlaube gestaffelte Einstiege
    max_scale_in_attempts: int = 2

# Default Parameter Set
MODERATE_PARAMS = {
    'name': 'Moderate Momentum Strategy',
    'description': 'MACD + Bollinger Band momentum strategy with adaptive risk management',
    'risk_level': 'moderate',
    'timeframe': 'daily',
    'enabled': True,
    'max_positions': 4,  # Weniger Positionen als conservative für bessere Kontrolle
    'min_confidence': 0.65,
    'strategy_type': 'momentum',
    'version': '1.0.0'
}

# Erstelle Standard-Konfiguration
MODERATE_CONFIG = ModerateConfig()

def validate_moderate_config(config: ModerateConfig) -> List[str]:
    """Validiert Moderate Strategy Konfiguration."""
    warnings = []
    
    # Position Size Validation
    if config.max_position_size > 0.15:  # 15% maximum
        warnings.append("max_position_size zu hoch (>15%)")
    if config.min_position_size >= config.max_position_size:
        warnings.append("min_position_size >= max_position_size")
    
    # MACD Validation
    if config.macd_fast_period >= config.macd_slow_period:
        warnings.append("MACD fast_period >= slow_period")
    
    # RSI Validation
    if config.rsi_oversold >= config.rsi_overbought:
        warnings.append("RSI oversold >= overbought")
    
    # Risk Management Validation
    if config.take_profit_ratio < 1.0:
        warnings.append("take_profit_ratio < 1.0 (negative risk/reward)")
    
    # ATR Validation
    if config.min_atr_percentage >= config.max_atr_percentage:
        warnings.append("min_atr_percentage >= max_atr_percentage")
    
    return warnings

# Initialisiere mit Standard-Profit-Taking Levels
if MODERATE_CONFIG.partial_profit_levels is None:
    MODERATE_CONFIG.partial_profit_levels = [0.5, 0.75]  # 50% und 75% Gewinnmitnahme

__all__ = ['ModerateConfig', 'MODERATE_CONFIG', 'MODERATE_PARAMS', 'validate_moderate_config']
