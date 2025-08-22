#!/usr/bin/env python3
"""
Google Credentials Test und Debugging
"""

import os
from dotenv import load_dotenv
import json

def test_google_credentials():
    """Testet Google Credentials aus .env"""
    load_dotenv()
    
    credentials = os.getenv('GOOGLE_CREDENTIALS')
    sheet_id = os.getenv('GOOGLE_SHEETS_ID')
    
    print("🔍 Google Credentials Test")
    print("=" * 40)
    
    if not credentials:
        print("❌ GOOGLE_CREDENTIALS ist leer oder nicht gesetzt")
        return False
    
    if not sheet_id:
        print("❌ GOOGLE_SHEETS_ID ist leer oder nicht gesetzt")
        return False
    
    print(f"✅ GOOGLE_SHEETS_ID gefunden: {sheet_id[:20]}...")
    print(f"✅ GOOGLE_CREDENTIALS gefunden: {len(credentials)} Zeichen")
    
    # Test JSON Parsing
    try:
        credentials_dict = json.loads(credentials)
        print(f"✅ JSON ist gültig")
        print(f"📋 Keys: {list(credentials_dict.keys())}")
        
        # Prüfe wichtige Felder
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in credentials_dict]
        
        if missing_fields:
            print(f"❌ Fehlende Felder: {missing_fields}")
            return False
        else:
            print("✅ Alle erforderlichen Felder vorhanden")
            print(f"📧 Client Email: {credentials_dict['client_email']}")
            print(f"🆔 Project ID: {credentials_dict['project_id']}")
            return True
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parsing Fehler: {e}")
        print(f"📄 Erste 100 Zeichen: {credentials[:100]}...")
        return False

if __name__ == "__main__":
    test_google_credentials()
