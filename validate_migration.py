"""
Validierungsskript für die Modularisierung der Krypto-Analyse-Plattform.

Testet alle Module und Abhängigkeiten vor dem Produktiv-Einsatz.
"""

import sys
import traceback
from pathlib import Path

def test_imports():
    """Testet alle wichtigen Imports."""
    print("🔍 Teste Module-Imports...")
    
    try:
        # Basis-Module
        import config
        print("✅ config.py erfolgreich importiert")
        
        from modules.utils.logger import logger, write_health_check
        print("✅ modules.utils.logger erfolgreich importiert")
        
        from modules.data_models import CoinAnalysisResult, MarketData
        print("✅ modules.data_models erfolgreich importiert")
        
        from modules.strategies.base_strategy import BaseStrategy
        print("✅ modules.strategies.base_strategy erfolgreich importiert")
        
        return True
        
    except Exception as e:
        print(f"❌ Import-Fehler: {e}")
        traceback.print_exc()
        return False

def test_config():
    """Testet die Konfiguration."""
    print("\n🔍 Teste Konfiguration...")
    
    try:
        from config import (
            API_CONFIG, COINS_TO_ANALYZE, validate_config, 
            get_api_credentials, STRATEGIES
        )
        
        # Teste Validierung
        warnings = validate_config()
        print(f"📋 Konfiguration validiert: {len(warnings)} Warnungen")
        
        for warning in warnings[:3]:  # Zeige nur erste 3
            print(f"  ⚠️ {warning}")
        
        # Teste API-Credentials
        credentials = get_api_credentials()
        print(f"🔑 API-Credentials verfügbar: {list(credentials.keys())}")
        
        # Teste Strategien
        enabled_strategies = [s.name for s in STRATEGIES.values() if s.enabled]
        print(f"🎯 Aktivierte Strategien: {enabled_strategies}")
        
        return True
        
    except Exception as e:
        print(f"❌ Konfigurationsfehler: {e}")
        traceback.print_exc()
        return False

def test_logger():
    """Testet das Logging-System."""
    print("\n🔍 Teste Logging-System...")
    
    try:
        from modules.utils.logger import logger, SecuritySanitizer
        
        # Teste verschiedene Log-Level
        logger.debug("Debug-Nachricht für Entwicklung")
        logger.info("Info-Nachricht - normale Operation")
        logger.warning("Warning-Nachricht - potentielles Problem")
        
        # Teste Security Sanitization
        test_message = "API Key: abc123def456 and secret token xyz789"
        sanitized = SecuritySanitizer.sanitize(test_message)
        print(f"🔒 Security Test: '{sanitized}'")
        
        # Teste Performance Tracking
        with logger.track_performance("test_operation"):
            import time
            time.sleep(0.1)  # Simuliere Operation
        
        print("✅ Logging-System funktioniert")
        return True
        
    except Exception as e:
        print(f"❌ Logging-Fehler: {e}")
        traceback.print_exc()
        return False

def test_legacy_compatibility():
    """Testet Rückwärtskompatibilität mit Test_script.py."""
    print("\n🔍 Teste Legacy-Kompatibilität...")
    
    try:
        # Teste ob Test_script.py die neuen Module nutzen kann
        import Test_script
        
        # Teste ob wichtige Funktionen noch verfügbar sind
        assert hasattr(Test_script, 'sanitize_error_message')
        assert hasattr(Test_script, 'escape_html')
        assert hasattr(Test_script, 'API_CONFIG')
        assert hasattr(Test_script, 'COINS_TO_ANALYZE')
        
        print("✅ Legacy-Kompatibilität gewährleistet")
        return True
        
    except Exception as e:
        print(f"❌ Legacy-Kompatibilitätsfehler: {e}")
        traceback.print_exc()
        return False

def test_data_models():
    """Testet die Datenmodelle."""
    print("\n🔍 Teste Datenmodelle...")
    
    try:
        from modules.data_models import (
            MarketData, TechnicalIndicators, NewsAnalysis, 
            TradingDecision, TradingSignal
        )
        from datetime import datetime
        
        # Erstelle Test-Datenstrukturen
        market_data = MarketData(
            symbol="BTC",
            price=50000.0,
            volume=1000000.0,
            timestamp=datetime.now(),
            high_24h=51000.0,
            low_24h=49000.0,
            change_24h=2.5
        )
        
        indicators = TechnicalIndicators(
            rsi=65.0,
            macd=0.001,
            macd_signal=0.0005,
            macd_histogram=0.0005,
            ma20=49500.0,
            ma50=48000.0,
            ma200=45000.0,
            bb_upper=51000.0,
            bb_lower=48000.0,
            bb_position=60.0,
            atr=1500.0,
            atr_percentage=3.0,
            stoch_k=70.0,
            williams_r=-30.0,
            volume_ratio=1.5
        )
        
        decision = TradingDecision(
            signal=TradingSignal.BUY,
            confidence=0.8,
            reasoning="Test decision",
            stop_loss=48000.0,
            take_profit=52000.0,
            position_size=0.1
        )
        
        print(f"📊 MarketData: {market_data.symbol} @ {market_data.price}")
        print(f"📈 Indicators: RSI {indicators.rsi}, MACD {indicators.macd}")
        print(f"🎯 Decision: {decision.signal.value} (confidence: {decision.confidence})")
        
        print("✅ Datenmodelle funktionieren")
        return True
        
    except Exception as e:
        print(f"❌ Datenmodell-Fehler: {e}")
        traceback.print_exc()
        return False

def main():
    """Hauptfunktion für die Validierung."""
    print("🚀 Starte Validierung der modularen Krypto-Analyse-Plattform")
    print("=" * 60)
    
    tests = [
        ("Module-Imports", test_imports),
        ("Konfiguration", test_config),
        ("Logging-System", test_logger),
        ("Datenmodelle", test_data_models),
        ("Legacy-Kompatibilität", test_legacy_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Schwerwiegender Fehler in {test_name}: {e}")
            results.append((test_name, False))
    
    # Zusammenfassung
    print("\n" + "=" * 60)
    print("📋 VALIDIERUNGS-ZUSAMMENFASSUNG")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ BESTANDEN" if success else "❌ FEHLGESCHLAGEN"
        print(f"{test_name:20} {status}")
        if success:
            passed += 1
    
    print(f"\nErgebnis: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("🎉 ALLE TESTS BESTANDEN - Migration erfolgreich!")
        print("🚀 Ready für Produktiv-Einsatz")
        return True
    else:
        print("⚠️ EINIGE TESTS FEHLGESCHLAGEN - Bitte Fehler beheben")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
