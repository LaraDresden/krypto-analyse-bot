"""
Conservative Trading Strategy Package.

Implementiert konservative Handelsstrategien mit:
- Trend-Following basierend auf MA200
- Niedrige Volatilitäts-Präferenz
- Starke Risk-Management Regeln
- Langfristige Positionen
"""

from .trend_strategy_simple import ConservativeTrendStrategy
from .config import CONSERVATIVE_CONFIG

__all__ = ['ConservativeTrendStrategy', 'CONSERVATIVE_CONFIG']
