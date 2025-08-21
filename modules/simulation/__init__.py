"""
Simulation Module für Backtesting und Portfolio-Management.

Dieses Modul enthält alle Funktionen für:
- Portfolio-Simulation (Real-time Multi-Strategy Management)
- Backtesting von Strategien (Historische Performance-Tests)
- Performance-Analyse
- Risiko-Management
"""

from .portfolio_simulator import PortfolioSimulator, SimulationPosition, SimulationResult
from .backtester import SimpleBacktester, BacktestTrade, BacktestResults

__all__ = [
    'PortfolioSimulator', 'SimulationPosition', 'SimulationResult',
    'SimpleBacktester', 'BacktestTrade', 'BacktestResults'
]
