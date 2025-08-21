"""
Moderate Trading Strategy Package.

Implementiert moderate Momentum-Strategien mit:
- MACD-basierte Momentum-Erkennung
- Bollinger Band Breakout-Signale  
- Volume-Bestätigung
- Adaptive Risk-Management
- Mittleres Risiko-Profil
"""

from .momentum_strategy import ModerateMomentumStrategy
from .config import MODERATE_CONFIG, MODERATE_PARAMS

__all__ = ['ModerateMomentumStrategy', 'MODERATE_CONFIG', 'MODERATE_PARAMS']
