"""
Test Suite für die modulare Krypto-Analyse-Plattform.

Testet die neue Strategien-Architektur und Portfolio-Simulation.
"""

import unittest
from datetime import datetime
from typing import Dict, Any

# Test Imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.data_models import MarketData, TechnicalIndicators, NewsAnalysis, TradingSignal
from modules.strategies.conservative.trend_strategy_simple import ConservativeTrendStrategy
from modules.simulation.portfolio_simulator import PortfolioSimulator

class TestConservativeStrategy(unittest.TestCase):
    """Test-Klasse für Conservative Strategy."""
    
    def setUp(self):
        """Setup für jeden Test."""
        self.strategy = ConservativeTrendStrategy()
        self.sample_market_data = MarketData(
            symbol='BTC',
            price=50000.0,
            volume=1000000.0,
            timestamp=datetime.now(),
            high_24h=52000.0,
            low_24h=48000.0,
            change_24h=2.5
        )
        
        self.sample_indicators = TechnicalIndicators(
            rsi=45.0,
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            ma20=49500.0,
            ma50=49000.0,
            ma200=48000.0,
            bb_upper=51000.0,
            bb_lower=47000.0,
            bb_position=60.0,
            atr=1000.0,
            atr_percentage=2.0,
            stoch_k=55.0,
            williams_r=-45.0,
            volume_ratio=1.2
        )
    
    def test_strategy_initialization(self):
        """Test ob Strategie korrekt initialisiert wird."""
        self.assertIsNotNone(self.strategy)
        self.assertEqual(self.strategy.name, 'Conservative Trend Following')
        self.assertIsNotNone(self.strategy.strategy_config)
    
    def test_bullish_signal(self):
        """Test für bullishes Signal."""
        # Bullish Setup: MA50 > MA200, RSI neutral, niedrige Volatilität
        decision = self.strategy.analyze('BTC', self.sample_market_data, self.sample_indicators)
        
        self.assertIn(decision.signal, [TradingSignal.BUY, TradingSignal.HOLD])
        self.assertIsInstance(decision.confidence, float)
        self.assertGreaterEqual(decision.confidence, 0.0)
        self.assertLessEqual(decision.confidence, 1.0)
        self.assertIsNotNone(decision.reasoning)
    
    def test_bearish_signal(self):
        """Test für bärisches Signal."""
        # Bearish Setup: MA50 < MA200
        bearish_indicators = TechnicalIndicators(
            rsi=75.0,  # Überkauft
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            ma20=49500.0,
            ma50=47000.0,  # MA50 < MA200
            ma200=48000.0,
            bb_upper=51000.0,
            bb_lower=47000.0,
            bb_position=80.0,
            atr=1000.0,
            atr_percentage=2.0,
            stoch_k=75.0,
            williams_r=-25.0,
            volume_ratio=1.2
        )
        
        decision = self.strategy.analyze('BTC', self.sample_market_data, bearish_indicators)
        
        self.assertIn(decision.signal, [TradingSignal.SELL, TradingSignal.HOLD])
    
    def test_risk_management(self):
        """Test Risk Management Funktionen."""
        decision = self.strategy.analyze('BTC', self.sample_market_data, self.sample_indicators)
        
        if decision.signal == TradingSignal.BUY:
            self.assertIsNotNone(decision.stop_loss)
            self.assertIsNotNone(decision.take_profit)
            self.assertLess(decision.stop_loss, self.sample_market_data.price)
            self.assertGreater(decision.take_profit, self.sample_market_data.price)
            self.assertGreater(decision.position_size, 0.0)
            self.assertLessEqual(decision.position_size, 0.05)  # Max 5%

class TestPortfolioSimulator(unittest.TestCase):
    """Test-Klasse für Portfolio Simulator."""
    
    def setUp(self):
        """Setup für jeden Test."""
        self.simulator = PortfolioSimulator(initial_balance=10000.0)
        self.strategy = ConservativeTrendStrategy()
        self.simulator.add_strategy(self.strategy)
        
        self.sample_market_data = MarketData(
            symbol='BTC',
            price=50000.0,
            volume=1000000.0,
            timestamp=datetime.now(),
            high_24h=52000.0,
            low_24h=48000.0,
            change_24h=2.5
        )
        
        self.sample_indicators = TechnicalIndicators(
            rsi=35.0,  # Leicht überverkauft
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            ma20=49500.0,
            ma50=49000.0,  # MA50 > MA200 (bullish)
            ma200=48000.0,
            bb_upper=51000.0,
            bb_lower=47000.0,
            bb_position=60.0,
            atr=1000.0,
            atr_percentage=2.0,  # Niedrige Volatilität
            stoch_k=40.0,
            williams_r=-60.0,
            volume_ratio=1.2
        )
    
    def test_simulator_initialization(self):
        """Test ob Simulator korrekt initialisiert wird."""
        self.assertEqual(self.simulator.initial_balance, 10000.0)
        self.assertEqual(self.simulator.current_balance, 10000.0)
        self.assertEqual(self.simulator.cash, 10000.0)
        self.assertEqual(len(self.simulator.positions), 0)
        self.assertEqual(len(self.simulator.strategies), 1)
    
    def test_process_market_data(self):
        """Test Marktdaten-Verarbeitung."""
        # Verarbeite Marktdaten
        self.simulator.process_market_data(
            'BTC', 
            self.sample_market_data, 
            self.sample_indicators
        )
        
        # Portfolio sollte updated sein
        self.assertGreaterEqual(len(self.simulator.balance_history), 1)
    
    def test_position_opening(self):
        """Test Position-Eröffnung."""
        # Verarbeite bullish Marktdaten
        self.simulator.process_market_data(
            'BTC', 
            self.sample_market_data, 
            self.sample_indicators
        )
        
        # Prüfe ob Position eröffnet wurde (abhängig von Strategie-Signal)
        status = self.simulator.get_current_status()
        self.assertIsInstance(status['positions_count'], int)
        self.assertGreaterEqual(status['positions_count'], 0)
    
    def test_performance_summary(self):
        """Test Performance-Zusammenfassung."""
        # Simuliere einige Trades
        self.simulator.process_market_data('BTC', self.sample_market_data, self.sample_indicators)
        
        summary = self.simulator.get_performance_summary()
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary.initial_balance, 10000.0)
        self.assertIsInstance(summary.total_return, float)
        self.assertIsInstance(summary.total_trades, int)
        self.assertIsInstance(summary.win_rate, float)

class TestIntegration(unittest.TestCase):
    """Integrationstests für das Gesamtsystem."""
    
    def test_strategy_simulator_integration(self):
        """Test Integration von Strategie und Simulator."""
        # Setup
        simulator = PortfolioSimulator(initial_balance=10000.0)
        strategy = ConservativeTrendStrategy()
        simulator.add_strategy(strategy)
        
        # Market Data
        market_data = MarketData(
            symbol='BTC',
            price=50000.0,
            volume=1000000.0,
            timestamp=datetime.now(),
            high_24h=52000.0,
            low_24h=48000.0,
            change_24h=2.5
        )
        
        indicators = TechnicalIndicators(
            rsi=35.0,
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            ma20=49500.0,
            ma50=49000.0,
            ma200=48000.0,
            bb_upper=51000.0,
            bb_lower=47000.0,
            bb_position=60.0,
            atr=1000.0,
            atr_percentage=2.0,
            stoch_k=40.0,
            williams_r=-60.0,
            volume_ratio=1.2
        )
        
        # Simuliere mehrere Market Updates
        for _ in range(5):
            simulator.process_market_data('BTC', market_data, indicators)
            # Leichte Preisveränderung für nächste Iteration
            market_data.price *= 1.01
        
        # Validate Results
        status = simulator.get_current_status()
        summary = simulator.get_performance_summary()
        
        self.assertIsInstance(status, dict)
        self.assertIsInstance(summary.total_return, float)
        self.assertGreaterEqual(len(simulator.balance_history), 1)

def run_tests():
    """Führt alle Tests aus."""
    print("🧪 Starte Tests für modulare Krypto-Analyse-Plattform...")
    print("=" * 60)
    
    # Test Suite erstellen
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Tests hinzufügen
    suite.addTests(loader.loadTestsFromTestCase(TestConservativeStrategy))
    suite.addTests(loader.loadTestsFromTestCase(TestPortfolioSimulator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Tests ausführen
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Ergebnis
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ Alle Tests bestanden!")
    else:
        print(f"❌ {len(result.failures)} Tests fehlgeschlagen")
        print(f"⚠️ {len(result.errors)} Fehler aufgetreten")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    run_tests()
