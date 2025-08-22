#!/usr/bin/env python3
"""Test-Skript um die Korrektur des rate_limit_delay Fehlers zu validieren."""

from config import API_CONFIG, TECHNICAL_CONFIG

print("=== CONFIG TEST ===")
print(f"API_CONFIG['rate_limit_delay']: {API_CONFIG['rate_limit_delay']}")
print(f"Typ: {type(API_CONFIG['rate_limit_delay'])}")

# Teste ob der Fehler jetzt behoben ist
try:
    delay = API_CONFIG['rate_limit_delay']
    print(f"✅ rate_limit_delay erfolgreich geladen: {delay}s")
except KeyError as e:
    print(f"❌ KeyError bei rate_limit_delay: {e}")

# Teste ob andere TECHNICAL_CONFIG Werte noch funktionieren
try:
    macd_threshold = TECHNICAL_CONFIG['macd_threshold']
    print(f"✅ TECHNICAL_CONFIG funktioniert: macd_threshold = {macd_threshold}")
except KeyError as e:
    print(f"❌ TECHNICAL_CONFIG Fehler: {e}")

print("=== TEST ABGESCHLOSSEN ===")
