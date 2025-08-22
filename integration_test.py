#!/usr/bin/env python3
"""
🔧 Vollständiger Integrationstest für das Krypto-Analyse System
Testet Backend → Google Sheets → Frontend Datenfluss
"""

import os
import json
import time
import subprocess
import sys
from pathlib import Path

def test_environment_setup():
    """Testet die Umgebungseinstellungen"""
    print("\n🔧 SCHRITT 1: Umgebungstest")
    print("=" * 50)
    
    # .env Datei prüfen
    if not Path('.env').exists():
        print("❌ .env Datei nicht gefunden!")
        return False
    
    # Credentials prüfen
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            'BITVAVO_API_KEY',
            'GEMINI_API_KEY', 
            'NEWS_API_KEY',
            'TELEGRAM_BOT_TOKEN',
            'GOOGLE_CREDENTIALS',
            'GOOGLE_SHEETS_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if not value or value == f'your_{var.lower()}_here':
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Fehlende Umgebungsvariablen: {', '.join(missing_vars)}")
            return False
        
        print("✅ Alle Umgebungsvariablen konfiguriert")
        return True
        
    except ImportError:
        print("❌ python-dotenv nicht installiert: pip install python-dotenv")
        return False
    except Exception as e:
        print(f"❌ Fehler beim Prüfen der Umgebung: {e}")
        return False

def test_dependencies():
    """Testet alle Python-Dependencies"""
    print("\n📦 SCHRITT 2: Dependency-Test")
    print("=" * 50)
    
    required_packages = [
        'pandas', 'numpy', 'requests', 'gspread', 
        'google-auth', 'python-dotenv', 'ccxt'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📥 Installiere fehlende Pakete: pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ Alle Dependencies verfügbar")
    return True

def test_backend_execution():
    """Testet die Backend-Ausführung"""
    print("\n🚀 SCHRITT 3: Backend-Test")
    print("=" * 50)
    
    try:
        # Test_script.py ausführen
        print("🔄 Führe Test_script.py aus...")
        result = subprocess.run(
            [sys.executable, 'Test_script.py'], 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 Minuten Timeout
        )
        
        if result.returncode == 0:
            print("✅ Backend erfolgreich ausgeführt")
            
            # Nach BUY-Signalen in der Ausgabe suchen
            if 'BUY' in result.stdout:
                print("✅ Trading-Signale generiert")
            
            # Nach Google Sheets Success suchen
            if 'Google Sheets' in result.stdout and ('Success' in result.stdout or 'erfolgreich' in result.stdout):
                print("✅ Google Sheets Integration funktioniert")
            
            return True
        else:
            print(f"❌ Backend-Fehler: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Backend-Timeout (>5 Minuten)")
        return False
    except Exception as e:
        print(f"❌ Backend-Ausführungsfehler: {e}")
        return False

def test_google_sheets_access():
    """Testet den Google Sheets Zugriff"""
    print("\n📊 SCHRITT 4: Google Sheets Test")
    print("=" * 50)
    
    try:
        from dotenv import load_dotenv
        import gspread
        
        load_dotenv()
        
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        sheets_id = os.getenv('GOOGLE_SHEETS_ID')
        
        if not credentials_json_str or not sheets_id:
            print("❌ Google Credentials oder Sheets ID fehlt")
            return False
        
        # Verbindung testen
        credentials_dict = json.loads(credentials_json_str)
        gc = gspread.service_account_from_dict(credentials_dict)
        
        # Spreadsheet öffnen
        try:
            spreadsheet = gc.open_by_key(sheets_id)
            print(f"✅ Spreadsheet gefunden: {spreadsheet.title}")
            
            # Worksheets auflisten
            worksheets = spreadsheet.worksheets()
            print(f"✅ {len(worksheets)} Worksheets verfügbar: {[ws.title for ws in worksheets]}")
            
            return True
            
        except gspread.SpreadsheetNotFound:
            print(f"❌ Spreadsheet mit ID {sheets_id} nicht gefunden")
            return False
            
    except json.JSONDecodeError:
        print("❌ Ungültiges JSON in GOOGLE_CREDENTIALS")
        return False
    except Exception as e:
        print(f"❌ Google Sheets Zugriffsfehler: {e}")
        return False

def test_frontend_files():
    """Testet Frontend-Dateien"""
    print("\n🌐 SCHRITT 5: Frontend-Test")
    print("=" * 50)
    
    frontend_files = ['index.html', 'index_v2.1.2.html']
    
    for file_name in frontend_files:
        if Path(file_name).exists():
            print(f"✅ {file_name} gefunden")
            
            # Google Sheets URL in der Datei prüfen
            with open(file_name, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'GOOGLE_SHEET_CSV_URL' in content:
                print(f"✅ {file_name} hat Google Sheets Integration")
            else:
                print(f"⚠️ {file_name} fehlt Google Sheets Integration")
        else:
            print(f"❌ {file_name} nicht gefunden")
    
    return True

def create_demo_data():
    """Erstellt Demo-Daten für Tests"""
    print("\n🎮 SCHRITT 6: Demo-Daten erstellen")
    print("=" * 50)
    
    try:
        # create_realistic_demo.py ausführen
        result = subprocess.run([sys.executable, 'create_realistic_demo.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Demo-Daten erfolgreich erstellt")
            print(result.stdout)
            return True
        else:
            print(f"❌ Demo-Daten Fehler: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Demo-Daten Ausführungsfehler: {e}")
        return False

def main():
    """Hauptfunktion für den Integrationstest"""
    print("🚀 KRYPTO-ANALYSE SYSTEM - VOLLSTÄNDIGER INTEGRATIONSTEST")
    print("=" * 70)
    
    tests = [
        ("Umgebungstest", test_environment_setup),
        ("Dependency-Test", test_dependencies),
        ("Google Sheets Test", test_google_sheets_access),
        ("Frontend-Test", test_frontend_files),
        ("Demo-Daten", create_demo_data),
        ("Backend-Test", test_backend_execution),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Unerwarteter Fehler in {test_name}: {e}")
            results.append((test_name, False))
    
    # Ergebnisse zusammenfassen
    print("\n" + "=" * 70)
    print("📋 TEST-ERGEBNISSE:")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ BESTANDEN" if success else "❌ FEHLGESCHLAGEN"
        print(f"{test_name:20} | {status}")
        if success:
            passed += 1
    
    print("=" * 70)
    print(f"📊 GESAMT: {passed}/{total} Tests bestanden ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALLE TESTS BESTANDEN! System ist bereit.")
        return True
    else:
        print("⚠️ Einige Tests fehlgeschlagen. Bitte beheben Sie die Probleme.")
        return False

if __name__ == "__main__":
    main()
