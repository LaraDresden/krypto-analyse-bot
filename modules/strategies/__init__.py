"""
Trading Strategies Package.

Zentrale Collection aller Trading-Strategien mit:
- BaseStrategy Interface
- Conservative, Moderate & Aggressive Strategy Kategorien  
- Zentrale Strategy Registry für Discovery und Management
"""

from .base_strategy import BaseStrategy, StrategyMetrics, StrategyPosition, TechnicalAnalysisHelpers, StrategyFactory
from .registry import StrategyRegistry, create_strategy, list_available_strategies, initialize_registry

# Auto-initialize registry when package is imported
_discovered_strategies = initialize_registry()

__version__ = "2.0.0"

__all__ = [
    'BaseStrategy', 'StrategyMetrics', 'StrategyPosition', 
    'TechnicalAnalysisHelpers', 'StrategyFactory',
    'StrategyRegistry', 'create_strategy', 'list_available_strategies',
    'initialize_registry'
]
