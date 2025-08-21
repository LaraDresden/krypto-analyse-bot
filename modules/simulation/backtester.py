"""
Simple Backtesting Engine - Historical Strategy Performance Testing.

Unterscheidet sich vom PortfolioSimulator durch:
- Historische Datenverarbeitung statt Real-Time
- Performance-Attribution nach Strategie
- Parameter-Sweep Unterstützung
- Detaillierte Trade-Statistiken
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np

from ..data_models import MarketData, TechnicalIndicators, TradingDecision, TradingSignal
from ..strategies.base_strategy import BaseStrategy
from ..utils.logger import logger

@dataclass
class BacktestTrade:
    """Ein einzelner Trade im Backtest."""
    strategy_name: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    signal: TradingSignal
    confidence: float
    reasoning: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    
    # Trade Results
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    duration_hours: float = 0.0
    exit_reason: str = ""
    is_winner: bool = False
    
    def calculate_results(self):
        """Berechnet Trade-Ergebnisse."""
        if self.exit_price and self.exit_time:
            self.pnl = (self.exit_price - self.entry_price) * self.quantity
            self.pnl_percentage = ((self.exit_price - self.entry_price) / self.entry_price) * 100
            self.duration_hours = (self.exit_time - self.entry_time).total_seconds() / 3600
            self.is_winner = self.pnl > 0

@dataclass
class BacktestResults:
    """Zusammenfassung der Backtest-Ergebnisse."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    
    # Performance Metrics
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Trade Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    avg_trade_duration: float = 0.0
    
    # Risk Metrics
    max_consecutive_losses: int = 0
    max_position_risk: float = 0.0
    value_at_risk_95: float = 0.0
    
    # Trade History
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)

class SimpleBacktester:
    """
    Einfacher Backtester für Strategy-Performance-Tests.
    
    Features:
    - Historische Datenverarbeitung
    - Multi-Strategy Support
    - Performance-Metriken
    - Trade-Tracking
    - Parameter-Sensitivity Analysis
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_trades: Dict[str, BacktestTrade] = {}  # symbol -> trade
        self.completed_trades: List[BacktestTrade] = []
        self.equity_history: List[Tuple[datetime, float]] = []
        
        logger.info(f"Backtester initialized with {initial_capital:.2f} capital")
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """Fügt eine Strategie zum Backtest hinzu."""
        self.strategies[strategy.name] = strategy
        logger.info(f"Added strategy: {strategy.name}")
    
    def run_backtest(self, historical_data: Dict[str, List[MarketData]], 
                    start_date: datetime, end_date: datetime) -> Dict[str, BacktestResults]:
        """
        Führt Backtest für alle Strategien über historische Daten aus.
        
        Args:
            historical_data: {symbol: [MarketData]} - Historische Kursdaten
            start_date: Backtest Startdatum
            end_date: Backtest Enddatum
            
        Returns:
            Dict mit BacktestResults pro Strategie
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Reset state
        self.current_capital = self.initial_capital
        self.active_trades.clear()
        self.completed_trades.clear()
        self.equity_history.clear()
        
        # Sammle alle verfügbaren Zeitpunkte
        all_timestamps = set()
        for symbol_data in historical_data.values():
            for data_point in symbol_data:
                if start_date <= data_point.timestamp <= end_date:
                    all_timestamps.add(data_point.timestamp)
        
        sorted_timestamps = sorted(all_timestamps)
        logger.info(f"Processing {len(sorted_timestamps)} time points")
        
        # Hauptschleife: Prozessiere jeden Zeitpunkt
        for i, timestamp in enumerate(sorted_timestamps):
            if i % 100 == 0:  # Progress logging
                logger.info(f"Processing {timestamp} ({i+1}/{len(sorted_timestamps)})")
            
            self._process_timestamp(timestamp, historical_data)
            
            # Record equity curve
            total_portfolio_value = self._calculate_portfolio_value(timestamp, historical_data)
            self.equity_history.append((timestamp, total_portfolio_value))
        
        # Close all remaining positions
        self._close_all_positions(end_date, historical_data)
        
        # Generate results per strategy
        return self._generate_results(start_date, end_date)
    
    def _process_timestamp(self, timestamp: datetime, 
                          historical_data: Dict[str, List[MarketData]]) -> None:
        """Prozessiert einen einzelnen Zeitpunkt."""
        
        # Für jedes Symbol aktuelle Daten holen
        for symbol, data_series in historical_data.items():
            current_data = None
            
            # Finde aktuellste Daten für diesen Zeitpunkt
            for data_point in data_series:
                if data_point.timestamp == timestamp:
                    current_data = data_point
                    break
            
            if not current_data:
                continue
            
            # Erstelle Mock-Indikatoren (in echtem Backtest würden diese berechnet)
            indicators = self._create_mock_indicators(current_data, symbol, data_series, timestamp)
            
            # Prüfe bestehende Positionen für Exit-Signale
            self._check_exit_conditions(symbol, current_data, indicators, timestamp)
            
            # Teste Entry-Signale für alle Strategien
            for strategy_name, strategy in self.strategies.items():
                if symbol not in self.active_trades:  # Keine Position offen
                    self._check_entry_signals(strategy, symbol, current_data, indicators, timestamp)
    
    def _create_mock_indicators(self, current_data: MarketData, symbol: str,
                               data_series: List[MarketData], timestamp: datetime) -> TechnicalIndicators:
        """Erstellt Mock-Indikatoren für Backtest (vereinfacht)."""
        
        # In einem echten Backtest würden hier echte technische Indikatoren berechnet
        # Für jetzt verwenden wir vereinfachte Mock-Werte
        
        # Sammle letzte 20 Preise für MA-Berechnung
        recent_prices = []
        for data_point in data_series:
            if data_point.timestamp <= timestamp:
                recent_prices.append(data_point.price)
        recent_prices = recent_prices[-50:]  # Letzte 50 für MA50
        
        # Einfache Moving Averages
        ma20 = np.mean(recent_prices[-20:]) if len(recent_prices) >= 20 else current_data.price
        ma50 = np.mean(recent_prices[-50:]) if len(recent_prices) >= 50 else current_data.price
        ma200 = ma50  # Vereinfacht
        
        # Mock RSI (zwischen 30-70)
        rsi = 50 + (hash(f"{symbol}{timestamp}") % 41 - 20)  # Pseudo-random 30-70
        
        # Mock MACD
        macd = (ma20 - ma50) / ma50 if ma50 > 0 else 0
        macd_signal = macd * 0.9
        macd_histogram = macd - macd_signal
        
        # Mock Bollinger Bands
        bb_upper = current_data.price * 1.02
        bb_lower = current_data.price * 0.98
        bb_position = ((current_data.price - bb_lower) / (bb_upper - bb_lower)) * 100
        
        # Mock ATR (2% des Preises)
        atr = current_data.price * 0.02
        atr_percentage = 2.0
        
        return TechnicalIndicators(
            rsi=float(rsi),
            macd=float(macd),
            macd_signal=float(macd_signal),
            macd_histogram=float(macd_histogram),
            ma20=float(ma20),
            ma50=float(ma50),
            ma200=float(ma200),
            bb_upper=float(bb_upper),
            bb_lower=float(bb_lower),
            bb_position=float(bb_position),
            atr=float(atr),
            atr_percentage=float(atr_percentage),
            stoch_k=50.0,
            williams_r=-50.0,
            volume_ratio=1.0
        )
    
    def _check_exit_conditions(self, symbol: str, current_data: MarketData,
                              indicators: TechnicalIndicators, timestamp: datetime) -> None:
        """Prüft Exit-Bedingungen für bestehende Positionen."""
        if symbol not in self.active_trades:
            return
        
        trade = self.active_trades[symbol]
        current_price = current_data.price
        
        # Stop Loss Check
        if trade.stop_loss and current_price <= trade.stop_loss:
            self._close_trade(trade, current_price, timestamp, "Stop Loss")
            return
        
        # Take Profit Check
        if trade.take_profit and current_price >= trade.take_profit:
            self._close_trade(trade, current_price, timestamp, "Take Profit")
            return
        
        # Strategy-basierte Exit-Signale
        strategy = self.strategies.get(trade.strategy_name)
        if strategy:
            decision = strategy.analyze(symbol, current_data, indicators, None)
            
            # Verkaufs-Signal bei bestehender Long-Position
            if decision.signal in [TradingSignal.SELL, TradingSignal.STRONG_SELL]:
                self._close_trade(trade, current_price, timestamp, f"Strategy Signal: {decision.signal}")
    
    def _check_entry_signals(self, strategy: BaseStrategy, symbol: str,
                           current_data: MarketData, indicators: TechnicalIndicators,
                           timestamp: datetime) -> None:
        """Prüft Entry-Signale für eine Strategie."""
        
        try:
            decision = strategy.analyze(symbol, current_data, indicators, None)
            
            # Nur Buy-Signale verarbeiten (Long-only Backtest)
            if decision.signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
                
                # Validiere Signal mit Strategy-eigener Logik
                if strategy.validate_signal(decision, symbol):
                    self._open_trade(strategy, symbol, current_data, indicators, decision, timestamp)
                    
        except Exception as e:
            logger.error(f"Error analyzing {symbol} with {strategy.name}: {e}")
    
    def _open_trade(self, strategy: BaseStrategy, symbol: str, market_data: MarketData,
                   indicators: TechnicalIndicators, decision: TradingDecision,
                   timestamp: datetime) -> None:
        """Öffnet eine neue Position."""
        
        # Berechne Positionsgröße basierend auf verfügbarem Kapital
        available_capital = self.current_capital * 0.8  # 80% max allocation
        position_value = available_capital * decision.position_size
        quantity = position_value / market_data.price
        
        # Erstelle Trade-Record
        trade = BacktestTrade(
            strategy_name=strategy.name,
            symbol=symbol,
            entry_time=timestamp,
            exit_time=None,
            entry_price=market_data.price,
            exit_price=None,
            quantity=quantity,
            signal=decision.signal,
            confidence=decision.confidence,
            reasoning=decision.reasoning,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit
        )
        
        self.active_trades[symbol] = trade
        
        # Update verfügbares Kapital
        self.current_capital -= position_value
        
        logger.debug(f"Opened {symbol} position: {quantity:.4f} @ {market_data.price:.4f}")
    
    def _close_trade(self, trade: BacktestTrade, exit_price: float,
                    exit_time: datetime, exit_reason: str) -> None:
        """Schließt eine bestehende Position."""
        
        # Update Trade-Details
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_reason = exit_reason
        trade.calculate_results()
        
        # Return capital
        position_value = trade.quantity * exit_price
        self.current_capital += position_value
        
        # Move to completed trades
        self.completed_trades.append(trade)
        del self.active_trades[trade.symbol]
        
        logger.debug(f"Closed {trade.symbol}: PnL {trade.pnl:.2f} ({trade.pnl_percentage:+.2f}%)")
    
    def _close_all_positions(self, end_date: datetime, 
                           historical_data: Dict[str, List[MarketData]]) -> None:
        """Schließt alle offenen Positionen am Ende des Backtests."""
        
        for symbol, trade in list(self.active_trades.items()):
            # Finde letzten verfügbaren Preis
            symbol_data = historical_data.get(symbol, [])
            last_price = None
            
            for data_point in reversed(symbol_data):
                if data_point.timestamp <= end_date:
                    last_price = data_point.price
                    break
            
            if last_price:
                self._close_trade(trade, last_price, end_date, "Backtest End")
    
    def _calculate_portfolio_value(self, timestamp: datetime,
                                 historical_data: Dict[str, List[MarketData]]) -> float:
        """Berechnet den Gesamtwert des Portfolios zu einem Zeitpunkt."""
        
        total_value = self.current_capital  # Cash
        
        # Add value of open positions
        for symbol, trade in self.active_trades.items():
            symbol_data = historical_data.get(symbol, [])
            current_price = None
            
            # Finde aktuellen Preis
            for data_point in symbol_data:
                if data_point.timestamp <= timestamp:
                    current_price = data_point.price
            
            if current_price:
                position_value = trade.quantity * current_price
                total_value += position_value
        
        return total_value
    
    def _generate_results(self, start_date: datetime, end_date: datetime) -> Dict[str, BacktestResults]:
        """Generiert Backtest-Ergebnisse pro Strategie."""
        
        # Gruppiere Trades nach Strategie
        trades_by_strategy: Dict[str, List[BacktestTrade]] = {}
        for trade in self.completed_trades:
            if trade.strategy_name not in trades_by_strategy:
                trades_by_strategy[trade.strategy_name] = []
            trades_by_strategy[trade.strategy_name].append(trade)
        
        results = {}
        
        for strategy_name, strategy_trades in trades_by_strategy.items():
            if not strategy_trades:
                continue
            
            # Basic calculations
            total_pnl = sum(trade.pnl for trade in strategy_trades)
            winning_trades = [t for t in strategy_trades if t.is_winner]
            losing_trades = [t for t in strategy_trades if not t.is_winner]
            
            # Performance metrics
            final_capital = self.initial_capital + total_pnl
            total_return_pct = (total_pnl / self.initial_capital) * 100
            
            # Trade statistics
            win_rate = len(winning_trades) / len(strategy_trades) if strategy_trades else 0
            avg_win = float(np.mean([t.pnl for t in winning_trades])) if winning_trades else 0.0
            avg_loss = float(np.mean([t.pnl for t in losing_trades])) if losing_trades else 0.0
            
            # Risk metrics
            daily_returns = [t.pnl_percentage for t in strategy_trades]
            sharpe_ratio = float(np.mean(daily_returns) / np.std(daily_returns)) if len(daily_returns) > 1 and np.std(daily_returns) > 0 else 0.0
            
            results[strategy_name] = BacktestResults(
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.initial_capital,
                final_capital=final_capital,
                total_return=total_pnl,
                total_return_pct=total_return_pct,
                sharpe_ratio=sharpe_ratio,
                total_trades=len(strategy_trades),
                winning_trades=len(winning_trades),
                losing_trades=len(losing_trades),
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                trades=strategy_trades,
                equity_curve=self.equity_history.copy()
            )
        
        return results
    
    def run_parameter_sweep(self, strategy_class: type, parameter_ranges: Dict[str, List],
                           historical_data: Dict[str, List[MarketData]],
                           start_date: datetime, end_date: datetime) -> Dict[str, BacktestResults]:
        """
        Führt Parameter-Sweep für eine Strategie durch.
        
        Args:
            strategy_class: Strategie-Klasse
            parameter_ranges: {param_name: [values]} für Sweep
            historical_data: Historische Daten
            start_date: Start-Datum
            end_date: End-Datum
            
        Returns:
            Dict mit Ergebnissen pro Parameter-Kombination
        """
        logger.info(f"Starting parameter sweep for {strategy_class.__name__}")
        
        # Generiere alle Parameter-Kombinationen
        import itertools
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        results = {}
        
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            param_key = "_".join([f"{k}={v}" for k, v in param_dict.items()])
            
            logger.info(f"Testing parameters: {param_dict}")
            
            # Erstelle Strategie mit diesen Parametern
            try:
                strategy = strategy_class(**param_dict)
                self.strategies.clear()
                self.add_strategy(strategy)
                
                # Führe Backtest aus
                backtest_results = self.run_backtest(historical_data, start_date, end_date)
                
                if strategy.name in backtest_results:
                    results[param_key] = backtest_results[strategy.name]
                    
            except Exception as e:
                logger.error(f"Error testing parameters {param_dict}: {e}")
                continue
        
        return results

__all__ = ['SimpleBacktester', 'BacktestTrade', 'BacktestResults']
