"""
Konfiguration für Conservative Trading Strategy.

Enthält alle strategiespezifischen Parameter für 
konservative Handelsansätze.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class ConservativeConfig:
    """Konfiguration für konservative Strategie."""
    
    # Risk Management
    max_position_size: float = 0.05  # Max 5% pro Position
    stop_loss_atr_multiplier: float = 2.0  # 2x ATR für Stop-Loss
    take_profit_ratio: float = 3.0  # 3:1 Risk-Reward Verhältnis
    max_portfolio_risk: float = 0.10  # Max 10% Portfolio-Risiko
    
    # Technische Indikatoren
    ma_long_period: int = 200  # MA200 für Haupttrend
    ma_short_period: int = 50  # MA50 für Signale
    rsi_oversold: float = 30.0  # RSI Überverkauft
    rsi_overbought: float = 70.0  # RSI Überkauft
    
    # Volatilitäts-Filter
    max_atr_percentage: float = 3.0  # Max 3% ATR für Einstieg
    min_volume_ratio: float = 0.8  # Min 80% Durchschnittsvolumen
    
    # Trend-Filter
    require_ma_trend: bool = True  # Nur bei klarem MA-Trend handeln
    min_trend_strength: float = 0.02  # Min 2% Abstand zwischen MAs
    
    # Position Management
    scaling_in_steps: int = 2  # Positions-Aufbau in 2 Tranchen
    profit_taking_levels: Optional[List[float]] = None  # Gewinnmitnahme-Levels
    
    def __post_init__(self):
        if self.profit_taking_levels is None:
            self.profit_taking_levels = [0.5, 1.0]  # 50% bei 1:1, Rest bei 3:1

# Globale Konfiguration für konservative Strategie
CONSERVATIVE_CONFIG = ConservativeConfig()

# Zusätzliche strategiespezifische Parameter
CONSERVATIVE_PARAMS: Dict[str, Any] = {
    'name': 'Conservative Trend Following',
    'description': 'Langfristige Trend-Following Strategie mit starkem Risk Management',
    'timeframe': '1d',  # Tägliche Signale
    'holding_period_days': 30,  # Durchschnittliche Haltedauer
    'win_rate_target': 0.45,  # Angestrebte Trefferquote 45%
    'profit_factor_target': 2.0,  # Angestrebter Profit Factor
    'max_drawdown_limit': 0.08,  # Max 8% Drawdown
    
    # Signal-Bestätigung
    'confirmation_signals': [
        'ma_trend_bullish',  # MA50 > MA200
        'rsi_not_overbought',  # RSI < 70
        'low_volatility',  # ATR < 3%
        'volume_confirmation'  # Volume > 80% Durchschnitt
    ],
    
    # Exit-Bedingungen
    'exit_conditions': [
        'stop_loss_hit',
        'take_profit_hit', 
        'trend_reversal',  # MA50 kreuzt unter MA200
        'high_volatility'  # ATR > 5%
    ]
}

def validate_conservative_config() -> list:
    """Validiert die konservative Strategiekonfiguration."""
    warnings = []
    
    if CONSERVATIVE_CONFIG.max_position_size > 0.10:
        warnings.append("WARNUNG: Position Size > 10% ist sehr risikoreich für konservative Strategie")
    
    if CONSERVATIVE_CONFIG.stop_loss_atr_multiplier < 1.5:
        warnings.append("WARNUNG: Stop-Loss < 1.5x ATR könnte zu frühe Exits verursachen")
    
    if CONSERVATIVE_CONFIG.take_profit_ratio < 2.0:
        warnings.append("WARNUNG: Risk-Reward < 2:1 ist für konservative Strategie niedrig")
    
    return warnings
