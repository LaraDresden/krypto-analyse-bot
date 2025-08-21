"""
Portfolio Simulator für Backtesting und Live-Trading Simulation.

Dieses Modul simuliert ein Trading-Portfolio mit:
- Multi-Strategy Support
- Risk Management
- Performance Tracking
- Position Management
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from ..data_models import MarketData, TechnicalIndicators, NewsAnalysis, TradingDecision, TradingSignal
from ..strategies.base_strategy import BaseStrategy
from ..utils.logger import logger

@dataclass
class SimulationPosition:
    """Eine Position in der Simulation."""
    symbol: str
    strategy_name: str
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.entry_price
    
    def calculate_pnl(self, current_price: float) -> float:
        """Berechnet unrealisierten PnL."""
        return (current_price - self.entry_price) * self.quantity

@dataclass
class SimulationResult:
    """Ergebnis einer Portfolio-Simulation."""
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    positions_history: List[Dict] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)

class PortfolioSimulator:
    """
    Portfolio Simulator für Backtesting und Live-Simulation.
    
    Verwaltet mehrere Strategien gleichzeitig und simuliert
    realistische Trading-Bedingungen.
    """
    
    def __init__(self, initial_balance: float = 10000.0, max_positions: int = 10):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.cash = initial_balance
        self.max_positions = max_positions
        
        # Portfolio State
        self.positions: Dict[str, SimulationPosition] = {}
        self.strategies: Dict[str, BaseStrategy] = {}
        self.trade_history: List[Dict] = []
        self.balance_history: List[Dict] = []
        
        # Performance Tracking
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.start_time = datetime.now()
        
        logger.info(f"Portfolio Simulator initialized with ${initial_balance:,.2f}")
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Fügt eine Strategie zum Portfolio hinzu."""
        self.strategies[strategy.name] = strategy
        logger.info(f"Strategy added: {strategy.name}")
    
    def process_market_data(self, symbol: str, market_data: MarketData, 
                           indicators: TechnicalIndicators, 
                           news: Optional[NewsAnalysis] = None) -> None:
        """
        Verarbeitet Marktdaten für alle Strategien.
        
        Args:
            symbol: Trading Symbol (z.B. 'BTC')
            market_data: Aktuelle Marktdaten
            indicators: Technische Indikatoren
            news: Optional News-Analyse
        """
        current_price = market_data.price
        
        # 1. Update bestehende Positionen
        self._update_positions(symbol, current_price)
        
        # 2. Führe Strategien aus
        for strategy_name, strategy in self.strategies.items():
            try:
                decision = strategy.analyze(symbol, market_data, indicators, news)
                self._process_trading_decision(symbol, strategy_name, decision, current_price)
            except Exception as e:
                logger.error(f"Strategy {strategy_name} error: {e}")
        
        # 3. Update Portfolio-Wert
        self._update_portfolio_value()
        
        # 4. Risk Management
        self._apply_risk_management()
    
    def _update_positions(self, symbol: str, current_price: float) -> None:
        """Updated alle Positionen für ein Symbol."""
        positions_to_close = []
        
        for pos_id, position in self.positions.items():
            if position.symbol == symbol:
                # Stop-Loss Check
                if position.stop_loss and current_price <= position.stop_loss:
                    self._close_position(pos_id, current_price, "Stop-Loss")
                    positions_to_close.append(pos_id)
                
                # Take-Profit Check
                elif position.take_profit and current_price >= position.take_profit:
                    self._close_position(pos_id, current_price, "Take-Profit")
                    positions_to_close.append(pos_id)
        
        # Entferne geschlossene Positionen
        for pos_id in positions_to_close:
            del self.positions[pos_id]
    
    def _process_trading_decision(self, symbol: str, strategy_name: str, 
                                 decision: TradingDecision, current_price: float) -> None:
        """Verarbeitet eine Trading-Entscheidung."""
        
        if decision.signal == TradingSignal.BUY:
            self._open_long_position(symbol, strategy_name, decision, current_price)
        
        elif decision.signal == TradingSignal.SELL:
            self._close_positions_for_symbol(symbol, current_price, "Strategy Signal")
        
        elif decision.signal == TradingSignal.STRONG_BUY:
            # Größere Position bei starkem Signal
            enhanced_decision = TradingDecision(
                signal=decision.signal,
                confidence=decision.confidence,
                reasoning=decision.reasoning,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                position_size=min(decision.position_size * 1.5, 0.10)  # Max 10%
            )
            self._open_long_position(symbol, strategy_name, enhanced_decision, current_price)
    
    def _open_long_position(self, symbol: str, strategy_name: str, 
                           decision: TradingDecision, current_price: float) -> None:
        """Öffnet eine Long-Position."""
        
        # Prüfe ob bereits Position für dieses Symbol/Strategie existiert
        existing_pos = self._get_position(symbol, strategy_name)
        if existing_pos:
            logger.info(f"Position already exists for {symbol} with {strategy_name}")
            return
        
        # Prüfe maximale Anzahl Positionen
        if len(self.positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached")
            return
        
        # Berechne Position Size
        position_value = self.current_balance * decision.position_size
        quantity = position_value / current_price
        
        # Prüfe verfügbares Cash
        if position_value > self.cash:
            logger.warning(f"Insufficient cash for position: ${position_value:,.2f} > ${self.cash:,.2f}")
            return
        
        # Erstelle Position
        position_id = f"{symbol}_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        position = SimulationPosition(
            symbol=symbol,
            strategy_name=strategy_name,
            entry_price=current_price,
            quantity=quantity,
            entry_time=datetime.now(),
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit
        )
        
        self.positions[position_id] = position
        self.cash -= position_value
        
        # Log Trade
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'strategy': strategy_name,
            'action': 'BUY',
            'price': current_price,
            'quantity': quantity,
            'value': position_value,
            'reasoning': decision.reasoning
        })
        
        logger.info(f"Opened position: {symbol} @ ${current_price:.2f} (${position_value:,.2f})")
    
    def _close_position(self, position_id: str, current_price: float, reason: str) -> None:
        """Schließt eine Position."""
        position = self.positions[position_id]
        close_value = position.quantity * current_price
        pnl = position.calculate_pnl(current_price)
        
        self.cash += close_value
        
        # Log Trade
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': position.symbol,
            'strategy': position.strategy_name,
            'action': 'SELL',
            'price': current_price,
            'quantity': position.quantity,
            'value': close_value,
            'pnl': pnl,
            'reason': reason,
            'hold_duration': (datetime.now() - position.entry_time).days
        })
        
        logger.info(f"Closed position: {position.symbol} @ ${current_price:.2f} "
                   f"PnL: ${pnl:+.2f} ({reason})")
    
    def _close_positions_for_symbol(self, symbol: str, current_price: float, reason: str) -> None:
        """Schließt alle Positionen für ein Symbol."""
        positions_to_close = [
            pos_id for pos_id, pos in self.positions.items() 
            if pos.symbol == symbol
        ]
        
        for pos_id in positions_to_close:
            self._close_position(pos_id, current_price, reason)
            del self.positions[pos_id]
    
    def _get_position(self, symbol: str, strategy_name: str) -> Optional[SimulationPosition]:
        """Sucht nach bestehender Position."""
        for position in self.positions.values():
            if position.symbol == symbol and position.strategy_name == strategy_name:
                return position
        return None
    
    def _update_portfolio_value(self) -> None:
        """Updated den Gesamt-Portfolio-Wert."""
        positions_value = sum(pos.current_value for pos in self.positions.values())
        self.current_balance = self.cash + positions_value
        
        # Update Peak und Drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Speichere Balance History
        self.balance_history.append({
            'timestamp': datetime.now(),
            'total_balance': self.current_balance,
            'cash': self.cash,
            'positions_value': positions_value,
            'positions_count': len(self.positions)
        })
    
    def _apply_risk_management(self) -> None:
        """Wendet Risk Management Regeln an."""
        
        # Max Drawdown Protection
        if self.max_drawdown > 0.15:  # 15% Max Drawdown
            logger.warning(f"Max drawdown exceeded: {self.max_drawdown:.1%}")
            # Schließe alle Positionen bei zu hohem Drawdown
            for pos_id in list(self.positions.keys()):
                position = self.positions[pos_id]
                # Aktuelle Preise müssten hier übergeben werden
                # Vereinfacht: Schließe mit Entry-Preis
                self._close_position(pos_id, position.entry_price, "Risk Management")
                del self.positions[pos_id]
    
    def get_performance_summary(self) -> SimulationResult:
        """Erstellt eine Performance-Zusammenfassung."""
        total_trades = len(self.trade_history)
        winning_trades = len([t for t in self.trade_history if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in self.trade_history if t.get('pnl', 0) < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        total_return = (self.current_balance - self.initial_balance) / self.initial_balance
        
        # Vereinfachte Sharpe Ratio Berechnung
        daily_returns = self._calculate_daily_returns()
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        
        return SimulationResult(
            start_date=self.start_time,
            end_date=datetime.now(),
            initial_balance=self.initial_balance,
            final_balance=self.current_balance,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            positions_history=self.trade_history,
            daily_returns=daily_returns
        )
    
    def _calculate_daily_returns(self) -> List[float]:
        """Berechnet tägliche Returns."""
        if len(self.balance_history) < 2:
            return [0.0]
        
        daily_returns = []
        for i in range(1, len(self.balance_history)):
            prev_balance = self.balance_history[i-1]['total_balance']
            curr_balance = self.balance_history[i]['total_balance']
            daily_return = (curr_balance - prev_balance) / prev_balance
            daily_returns.append(daily_return)
        
        return daily_returns
    
    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """Berechnet Sharpe Ratio (vereinfacht)."""
        if not daily_returns:
            return 0.0
        
        avg_return = sum(daily_returns) / len(daily_returns)
        if avg_return == 0:
            return 0.0
        
        variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Annualisierte Sharpe Ratio (252 Trading-Tage)
        return (avg_return * 252) / (std_dev * (252 ** 0.5))
    
    def get_current_status(self) -> Dict[str, Any]:
        """Gibt aktuellen Portfolio-Status zurück."""
        positions_value = sum(pos.current_value for pos in self.positions.values())
        
        return {
            'timestamp': datetime.now(),
            'total_balance': self.current_balance,
            'cash': self.cash,
            'positions_value': positions_value,
            'positions_count': len(self.positions),
            'total_return': (self.current_balance - self.initial_balance) / self.initial_balance,
            'max_drawdown': self.max_drawdown,
            'active_strategies': list(self.strategies.keys()),
            'positions': [
                {
                    'symbol': pos.symbol,
                    'strategy': pos.strategy_name,
                    'entry_price': pos.entry_price,
                    'quantity': pos.quantity,
                    'current_value': pos.current_value,
                    'unrealized_pnl': pos.calculate_pnl(pos.entry_price),  # Würde aktuellen Preis benötigen
                    'entry_time': pos.entry_time
                }
                for pos in self.positions.values()
            ]
        }
