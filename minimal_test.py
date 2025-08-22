#!/usr/bin/env python3
"""
🧪 Schneller Minimal-Test ohne echte Credentials
Testet grundlegende Funktionalität mit Demo-Daten
"""

import os
import sys
from pathlib import Path

def test_basic_functionality():
    """Minimaler Test der Grundfunktionen"""
    print("MINIMAL-TEST: Grundfunktionen")
    print("=" * 40)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Python Dateien vorhanden
    tests_total += 1
    required_files = ['Test_script.py', 'config.py', 'performance_tracker.py']
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if not missing_files:
        print("✅ Alle Python-Dateien vorhanden")
        tests_passed += 1
    else:
        print(f"❌ Fehlende Dateien: {missing_files}")
    
    # Test 2: Frontend Dateien
    tests_total += 1
    frontend_files = ['index.html', 'index_v2.1.2.html']
    frontend_exists = any(Path(f).exists() for f in frontend_files)
    
    if frontend_exists:
        print("✅ Frontend-Dateien vorhanden")
        tests_passed += 1
    else:
        print("❌ Keine Frontend-Dateien gefunden")
    
    # Test 3: .env Template
    tests_total += 1
    if Path('.env').exists():
        print("✅ .env Datei vorhanden")
        tests_passed += 1
    else:
        print("❌ .env Datei fehlt")
    
    # Test 4: Demo-Daten
    tests_total += 1
    if Path('demo_trading_signals.json').exists():
        print("✅ Demo-Daten verfügbar")
        tests_passed += 1
    else:
        print("❌ Demo-Daten nicht gefunden")
    
    # Test 5: Modules
    tests_total += 1
    if Path('modules').exists() and Path('modules/__init__.py').exists():
        print("✅ Module-Struktur korrekt")
        tests_passed += 1
    else:
        print("❌ Module-Struktur fehlt")
    
    print("=" * 40)
    print(f"Ergebnis: {tests_passed}/{tests_total} Tests bestanden")
    
    if tests_passed == tests_total:
        print("🎉 GRUNDFUNKTIONEN OK - System ist strukturell bereit!")
        return True
    else:
        print("⚠️ Einige Grundkomponenten fehlen")
        return False

def test_imports():
    """Testet wichtige Python-Imports"""
    print("\nIMPORT-TEST: Python-Module")
    print("=" * 40)
    
    tests_passed = 0
    tests_total = 0
    
    test_modules = [
        ('pandas', 'Datenverarbeitung'),
        ('json', 'JSON-Handling'), 
        ('os', 'Betriebssystem'),
        ('datetime', 'Zeit/Datum'),
        ('pathlib', 'Dateipfade')
    ]
    
    for module_name, description in test_modules:
        tests_total += 1
        try:
            __import__(module_name)
            print(f"✅ {module_name} ({description})")
            tests_passed += 1
        except ImportError:
            print(f"❌ {module_name} ({description}) - Modul fehlt")
    
    print("=" * 40)
    print(f"Imports: {tests_passed}/{tests_total} erfolgreich")
    return tests_passed == tests_total

def main():
    """Hauptfunktion für Minimal-Test"""
    print("🧪 KRYPTO-ANALYSE SYSTEM - MINIMAL-TEST")
    print("=" * 50)
    print("Testet Grundfunktionen ohne echte API-Credentials")
    print("=" * 50)
    
    # Grundfunktionen testen
    basic_ok = test_basic_functionality()
    
    # Imports testen  
    imports_ok = test_imports()
    
    # Gesamtergebnis
    print("\n" + "=" * 50)
    print("GESAMT-ERGEBNIS:")
    print("=" * 50)
    
    if basic_ok and imports_ok:
        print("🎉 MINIMAL-TEST BESTANDEN!")
        print("")
        print("Nächste Schritte:")
        print("1. Echte API-Credentials in .env eintragen")
        print("2. python Test_script.py ausführen")
        print("3. index_v2.1.2.html im Browser öffnen")
        return True
    else:
        print("❌ MINIMAL-TEST FEHLGESCHLAGEN")
        print("Bitte beheben Sie die Grundprobleme zuerst.")
        return False

if __name__ == "__main__":
    main()
