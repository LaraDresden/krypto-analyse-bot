"""
Strategy Registry - Zentrale Registrierung und Discovery für Trading-Strategien.

Ermöglicht:
- Automatische Strategie-Entdeckung
- Plugin-ähnliche Architektur  
- Einfache Integration neuer Strategien
- Konfiguration per Name
"""

from typing import Dict, List, Type, Optional, Any
from abc import ABC

from ..strategies.base_strategy import BaseStrategy
from ..utils.logger import logger

class StrategyRegistry:
    """
    Zentrale Registry für alle verfügbaren Trading-Strategien.
    
    Funktioniert als Factory Pattern mit automatischer Entdeckung.
    """
    
    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _instances: Dict[str, BaseStrategy] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[BaseStrategy], 
                description: str = "", category: str = "general") -> None:
        """
        Registriert eine neue Strategie-Klasse.
        
        Args:
            name: Eindeutiger Name der Strategie
            strategy_class: Strategie-Klasse (muss BaseStrategy erweitern)
            description: Beschreibung der Strategie
            category: Kategorie (conservative, moderate, aggressive)
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"Strategy class {strategy_class.__name__} must extend BaseStrategy")
        
        cls._strategies[name] = strategy_class
        
        # Erweiterte Metadaten als Class-Attribute setzen
        setattr(strategy_class, '_registry_name', name)
        setattr(strategy_class, '_registry_description', description)
        setattr(strategy_class, '_registry_category', category)
        
        logger.info(f"Strategy registered: {name} ({category})")
    
    @classmethod
    def create(cls, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseStrategy]:
        """
        Erstellt eine Instanz einer registrierten Strategie.
        
        Args:
            name: Name der Strategie
            config: Optional Konfiguration
            
        Returns:
            Strategy-Instanz oder None wenn nicht gefunden
        """
        if name not in cls._strategies:
            logger.error(f"Strategy '{name}' not found in registry")
            return None
        
        try:
            strategy_class = cls._strategies[name]
            
            # Strategies haben ihre eigene Initialisierung ohne Parameter
            instance = strategy_class()  # type: ignore
            
            # Cache Instance für spätere Wiederverwendung
            cls._instances[name] = instance
            
            logger.info(f"Strategy instance created: {name}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to create strategy '{name}': {e}")
            return None
    
    @classmethod
    def get_instance(cls, name: str) -> Optional[BaseStrategy]:
        """
        Holt eine bereits erstellte Instanz oder erstellt eine neue.
        
        Args:
            name: Name der Strategie
            
        Returns:
            Strategy-Instanz oder None
        """
        if name in cls._instances:
            return cls._instances[name]
        
        return cls.create(name)
    
    @classmethod
    def list_strategies(cls) -> List[Dict[str, Any]]:
        """
        Gibt eine Liste aller registrierten Strategien zurück.
        
        Returns:
            Liste von Strategy-Metadaten
        """
        strategies = []
        
        for name, strategy_class in cls._strategies.items():
            # Hole Metadaten aus den Registry-Attributen
            description = getattr(strategy_class, '_registry_description', 'No description')
            category = getattr(strategy_class, '_registry_category', 'general')
            
            strategies.append({
                'name': name,
                'class_name': strategy_class.__name__,
                'description': description,
                'category': category,
                'module': strategy_class.__module__,
                'available': True
            })
        
        return strategies
    
    @classmethod
    def get_strategies_by_category(cls, category: str) -> List[str]:
        """
        Gibt alle Strategien einer bestimmten Kategorie zurück.
        
        Args:
            category: Kategorie (conservative, moderate, aggressive)
            
        Returns:
            Liste von Strategy-Namen
        """
        strategies = []
        
        for name, strategy_class in cls._strategies.items():
            category_attr = getattr(strategy_class, '_registry_category', 'general')
            if category_attr == category:
                strategies.append(name)
        
        return strategies
    
    @classmethod
    def clear(cls) -> None:
        """Leert die Registry (hauptsächlich für Tests)."""
        cls._strategies.clear()
        cls._instances.clear()
        logger.info("Strategy registry cleared")
    
    @classmethod
    def auto_discover(cls) -> int:
        """
        Automatische Entdeckung und Registrierung aller verfügbaren Strategien.
        
        Returns:
            Anzahl entdeckter Strategien
        """
        discovered = 0
        
        try:
            # Conservative Strategien
            from ..strategies.conservative import ConservativeTrendStrategy
            cls.register(
                "conservative_trend",
                ConservativeTrendStrategy,
                "Trend-following strategy with conservative risk management",
                "conservative"
            )
            discovered += 1
            
        except ImportError as e:
            logger.warning(f"Could not import conservative strategies: {e}")
        
        try:
            # Moderate Strategien
            from ..strategies.moderate import ModerateMomentumStrategy
            cls.register(
                "moderate_momentum", 
                ModerateMomentumStrategy,
                "MACD + Bollinger Band momentum strategy with adaptive risk management",
                "moderate"
            )
            discovered += 1
            
        except ImportError as e:
            logger.warning(f"Could not import moderate strategies: {e}")
        
        # Füge hier weitere Auto-Discovery für aggressive Strategien hinzu
        # try:
        #     from ..strategies.aggressive import AggressiveScalpingStrategy
        #     cls.register("aggressive_scalping", AggressiveScalpingStrategy, ...)
        # except ImportError:
        #     pass
        
        logger.info(f"Auto-discovered {discovered} strategies")
        return discovered
    
    @classmethod
    def validate_registry(cls) -> Dict[str, List[str]]:
        """
        Validiert alle registrierten Strategien.
        
        Returns:
            Dict mit 'valid' und 'invalid' Strategy-Listen
        """
        valid = []
        invalid = []
        
        for name, strategy_class in cls._strategies.items():
            try:
                # Teste ob Instanz erstellt werden kann
                instance = cls.create(name)
                if instance:
                    # Teste ob required methods existieren
                    if hasattr(instance, 'analyze') and hasattr(instance, 'get_parameters'):
                        valid.append(name)
                    else:
                        invalid.append(f"{name}: Missing required methods")
                else:
                    invalid.append(f"{name}: Cannot create instance")
                    
            except Exception as e:
                invalid.append(f"{name}: {str(e)}")
        
        logger.info(f"Registry validation: {len(valid)} valid, {len(invalid)} invalid strategies")
        return {'valid': valid, 'invalid': invalid}


# Factory Functions für einfache Verwendung
def create_strategy(name: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseStrategy]:
    """
    Convenience-Funktion zum Erstellen einer Strategie.
    
    Args:
        name: Strategy-Name
        config: Optional Konfiguration
        
    Returns:
        Strategy-Instanz oder None
    """
    return StrategyRegistry.create(name, config)

def list_available_strategies() -> List[Dict[str, Any]]:
    """
    Convenience-Funktion zum Auflisten verfügbarer Strategien.
    
    Returns:
        Liste von Strategy-Metadaten
    """
    return StrategyRegistry.list_strategies()

def get_conservative_strategies() -> List[str]:
    """Gibt alle konservativen Strategien zurück."""
    return StrategyRegistry.get_strategies_by_category("conservative")

def get_moderate_strategies() -> List[str]:
    """Gibt alle moderaten Strategien zurück."""
    return StrategyRegistry.get_strategies_by_category("moderate")

def get_aggressive_strategies() -> List[str]:
    """Gibt alle aggressiven Strategien zurück."""
    return StrategyRegistry.get_strategies_by_category("aggressive")

# Auto-Discovery beim Import
def initialize_registry() -> int:
    """
    Initialisiert die Registry mit allen verfügbaren Strategien.
    
    Returns:
        Anzahl entdeckter Strategien
    """
    return StrategyRegistry.auto_discover()

__all__ = [
    'StrategyRegistry',
    'create_strategy', 
    'list_available_strategies',
    'get_conservative_strategies',
    'get_moderate_strategies', 
    'get_aggressive_strategies',
    'initialize_registry'
]
