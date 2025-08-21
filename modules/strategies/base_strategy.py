"""
Base Strategy Interface und Abstract Classes für Trading-Strategien.

Definiert die Grundstruktur für alle Handelsstrategien und stellt
gemeinsame Funktionalitäten zur Verfügung.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

# Import unserer Datenmodelle
from ..data_models import (
    MarketData, TechnicalIndicators, NewsAnalysis, TradingDecision, 
    TradingSignal, VolatilityLevel, TrendDirection
)
from ..utils.logger import logger, handle_exceptions

@dataclass
class StrategyMetrics:
    """Performance-Metriken einer Strategie."""
    total_trades: int = 0
    winning_trades: int = 0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_trade_duration: float = 0.0
    profit_factor: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass 
class StrategyPosition:
    """Eine offene Position einer Strategie."""
    symbol: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str = ""
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.entry_price
    
    def calculate_pnl(self, current_price: float) -> float:
        """Berechnet unrealisierten PnL."""
        return (current_price - self.entry_price) * self.quantity

class BaseStrategy(ABC):
    """
    Abstrakte Basisklasse für alle Trading-Strategien.
    
    Jede Strategie muss diese Klasse erweitern und die abstrakten Methoden implementieren.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.metrics = StrategyMetrics()
        self.positions: Dict[str, StrategyPosition] = {}
        self.is_enabled = config.get('enabled', True)
        self.max_positions = config.get('max_positions', 5)
        self.risk_level = config.get('risk_level', 'moderate')
        
        logger.info(f"Strategy initialized: {name} (risk: {self.risk_level})")
    
    @abstractmethod
    def analyze(self, symbol: str, market_data: MarketData, 
               indicators: TechnicalIndicators, 
               news: Optional[NewsAnalysis] = None) -> TradingDecision:
        """
        Analysiert Marktdaten und gibt eine Handelsentscheidung zurück.
        
        Args:
            symbol: Trading-Symbol (z.B. 'BTC')
            market_data: Aktuelle Marktdaten
            indicators: Technische Indikatoren
            news: Optional News-Analyse
            
        Returns:
            TradingDecision mit Signal, Confidence und Reasoning
        """
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Gibt die aktuellen Strategie-Parameter zurück."""
        pass
    
    def validate_signal(self, decision: TradingDecision, symbol: str) -> bool:
        """
        Validiert ein Handelssignal basierend auf Risikomanagement.
        
        Args:
            decision: Die Handelsentscheidung
            symbol: Trading-Symbol
            
        Returns:
            True wenn Signal valide ist, False sonst
        """
        # Prüfe ob Strategie aktiviert ist
        if not self.is_enabled:
            logger.debug(f"Strategy {self.name} is disabled")
            return False
        
        # Prüfe Positions-Limit
        if decision.signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            if len(self.positions) >= self.max_positions:
                logger.warning(f"Strategy {self.name} has reached max positions ({self.max_positions})")
                return False
        
        # Prüfe Mindest-Confidence
        min_confidence = self.config.get('min_confidence', 0.6)
        if decision.confidence < min_confidence:
            logger.debug(f"Decision confidence {decision.confidence:.2f} below minimum {min_confidence}")
            return False
        
        # Prüfe Position Size
        if decision.position_size > 1.0 or decision.position_size <= 0:
            logger.warning(f"Invalid position size: {decision.position_size}")
            return False
        
        return True
    
    @handle_exceptions("strategy_update_position")
    def update_position(self, symbol: str, current_price: float) -> Optional[TradingDecision]:
        """
        Aktualisiert eine bestehende Position und prüft Exit-Bedingungen.
        
        Args:
            symbol: Trading-Symbol
            current_price: Aktueller Preis
            
        Returns:
            Optional TradingDecision für Exit-Signal
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        pnl = position.calculate_pnl(current_price)
        pnl_percentage = (pnl / position.current_value) * 100
        
        # Stop Loss Check
        if position.stop_loss and current_price <= position.stop_loss:
            logger.info(f"Stop loss triggered for {symbol} at {current_price}")
            return TradingDecision(
                signal=TradingSignal.SELL,
                confidence=1.0,
                reasoning=f"Stop loss triggered at {current_price}",
                stop_loss=None,
                take_profit=None,
                position_size=1.0  # Close full position
            )
        
        # Take Profit Check
        if position.take_profit and current_price >= position.take_profit:
            logger.info(f"Take profit triggered for {symbol} at {current_price}")
            return TradingDecision(
                signal=TradingSignal.SELL,
                confidence=1.0,
                reasoning=f"Take profit triggered at {current_price}",
                stop_loss=None,
                take_profit=None,
                position_size=1.0  # Close full position
            )
        
        # Log Position Status
        logger.debug(f"Position {symbol}: PnL {pnl_percentage:+.2f}%")
        
        return None
    
    def add_position(self, symbol: str, price: float, quantity: float, 
                    stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                    reasoning: str = ""):
        """Fügt eine neue Position hinzu."""
        position = StrategyPosition(
            symbol=symbol,
            entry_price=price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning
        )
        self.positions[symbol] = position
        
        logger.info(f"Added position: {symbol} @ {price:.4f} (qty: {quantity:.4f})")
    
    def close_position(self, symbol: str) -> Optional[StrategyPosition]:
        """Schließt eine Position und gibt sie zurück."""
        if symbol in self.positions:
            position = self.positions.pop(symbol)
            logger.info(f"Closed position: {symbol}")
            return position
        return None
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Berechnet den aktuellen Portfolio-Wert."""
        total_value = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                total_value += position.quantity * current_price
        return total_value
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Gibt eine Zusammenfassung des Strategie-Status zurück."""
        return {
            'name': self.name,
            'enabled': self.is_enabled,
            'risk_level': self.risk_level,
            'positions_count': len(self.positions),
            'max_positions': self.max_positions,
            'metrics': {
                'total_trades': self.metrics.total_trades,
                'win_rate': self.metrics.win_rate,
                'total_return': self.metrics.total_return,
                'sharpe_ratio': self.metrics.sharpe_ratio
            }
        }
    
    def update_metrics(self, trade_return: float, trade_duration: float):
        """Aktualisiert Performance-Metriken nach einem Trade."""
        self.metrics.total_trades += 1
        if trade_return > 0:
            self.metrics.winning_trades += 1
        
        self.metrics.total_return += trade_return
        self.metrics.win_rate = self.metrics.winning_trades / self.metrics.total_trades
        
        # Aktualisiere durchschnittliche Trade-Dauer
        prev_avg = self.metrics.avg_trade_duration
        n = self.metrics.total_trades
        self.metrics.avg_trade_duration = ((prev_avg * (n-1)) + trade_duration) / n
        
        self.metrics.last_updated = datetime.now()
        
        logger.info(f"Updated metrics for {self.name}: Win rate {self.metrics.win_rate:.1%}, Total return {self.metrics.total_return:+.2f}%")

class TechnicalAnalysisHelpers:
    """Hilfsfunktionen für technische Analyse, die von Strategien genutzt werden können."""
    
    @staticmethod
    def is_bullish_trend(indicators: TechnicalIndicators) -> bool:
        """Prüft ob ein bullischer Trend vorliegt."""
        return (indicators.ma20 > indicators.ma50 > indicators.ma200 and
                indicators.macd_histogram > 0)
    
    @staticmethod
    def is_bearish_trend(indicators: TechnicalIndicators) -> bool:
        """Prüft ob ein bärischer Trend vorliegt."""
        return (indicators.ma20 < indicators.ma50 < indicators.ma200 and
                indicators.macd_histogram < 0)
    
    @staticmethod
    def is_oversold(indicators: TechnicalIndicators, threshold: float = 30) -> bool:
        """Prüft ob der Markt überverkauft ist."""
        return indicators.rsi < threshold
    
    @staticmethod
    def is_overbought(indicators: TechnicalIndicators, threshold: float = 70) -> bool:
        """Prüft ob der Markt überkauft ist."""
        return indicators.rsi > threshold
    
    @staticmethod
    def is_high_volatility(indicators: TechnicalIndicators, threshold: float = 3.0) -> bool:
        """Prüft ob hohe Volatilität vorliegt."""
        return indicators.atr_percentage > threshold
    
    @staticmethod
    def calculate_position_size(balance: float, risk_per_trade: float, 
                              entry_price: float, stop_loss: float) -> float:
        """
        Berechnet optimale Position Size basierend auf Risikomanagement.
        
        Args:
            balance: Verfügbares Kapital
            risk_per_trade: Risiko pro Trade (z.B. 0.02 für 2%)
            entry_price: Einstiegspreis
            stop_loss: Stop-Loss Preis
            
        Returns:
            Optimale Position Size
        """
        if stop_loss >= entry_price:
            return 0.0  # Invalid stop loss
        
        risk_amount = balance * risk_per_trade
        price_risk = entry_price - stop_loss
        position_size = risk_amount / price_risk
        
        return min(position_size, balance * 0.2)  # Max 20% des Kapitals

class StrategyFactory:
    """Factory für die Erstellung von Strategy-Instanzen."""
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Registriert eine Strategie-Klasse."""
        cls._strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")
    
    @classmethod
    def create(cls, name: str, config: Dict[str, Any]) -> Optional[BaseStrategy]:
        """Erstellt eine Strategy-Instanz."""
        if name not in cls._strategies:
            logger.error(f"Unknown strategy: {name}")
            return None
        
        try:
            strategy_class = cls._strategies[name]
            return strategy_class(name, config)
        except Exception as e:
            logger.error(f"Failed to create strategy {name}: {e}")
            return None
    
    @classmethod
    def list_available(cls) -> List[str]:
        """Gibt eine Liste aller verfügbaren Strategien zurück."""
        return list(cls._strategies.keys())

__all__ = [
    'BaseStrategy', 'StrategyMetrics', 'StrategyPosition', 
    'TechnicalAnalysisHelpers', 'StrategyFactory'
]
