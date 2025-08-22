# 📊 Trading Performance Tracking System

## Übersicht

Das Trading Performance Tracking System analysiert die Erfolgsrate der KI-generierten Trading-Empfehlungen und bietet umfassende Performance-Metriken.

## 🎯 Features

### 📈 Performance-Analyse
- **Erfolgsrate-Tracking**: Prozentuale Erfolgsquote von BUY/SELL/HOLD Signalen
- **ROI-Berechnung**: Return on Investment für jedes Trading-Signal
- **Risiko-Metriken**: Sharpe Ratio, Maximum Drawdown, Volatilität
- **Zeitbasierte Analyse**: Performance über verschiedene Zeiträume

### 🔍 Detailierte Metriken
- **Nach Signal-Typ**: BUY vs SELL vs HOLD Performance
- **Nach Coin**: Welche Kryptowährungen die besten Ergebnisse liefern
- **Nach Konfidenz-Level**: Korrelation zwischen KI-Konfidenz und Erfolg
- **Nach Strategie**: Vergleich verschiedener Trading-Strategien

### 🚨 Automatisches Monitoring
- **Kontinuierliche Überwachung**: Alle 30 Minuten Performance-Check
- **Alert-System**: Telegram-Benachrichtigungen bei kritischen Ereignissen
- **Tägliche Reports**: Automatische Zusammenfassungen um 09:00 und 18:00
- **CSV-Export**: Daten für weitere Analyse exportieren

## 📂 Dateien

| Datei | Beschreibung |
|-------|--------------|
| `performance_tracker.py` | Hauptklasse für Performance-Analyse |
| `automated_performance_monitor.py` | Automatisches Monitoring-System |
| `PERFORMANCE_TRACKING.md` | Diese Dokumentation |

## 🚀 Verwendung

### 1. Einmalige Performance-Analyse

```bash
# Vollständige Analyse durchführen
python performance_tracker.py

# Ergebnis: Detaillierter Performance-Report in der Konsole
```

### 2. Automatisches Monitoring starten

```bash
# Kontinuierliches Monitoring (läuft bis Strg+C)
python automated_performance_monitor.py

# Einmaliger Performance-Check
python automated_performance_monitor.py check

# Einmaliger Report
python automated_performance_monitor.py report

# CSV-Export
python automated_performance_monitor.py export
```

## 📊 Performance-Metriken

### Grundlegende Kennzahlen
- **Gesamte Signale**: Anzahl der generierten Trading-Signale
- **Erfolgreiche Signale**: Signale mit positivem ROI
- **Erfolgsrate**: Prozentsatz erfolgreicher Signale
- **Durchschnittlicher ROI**: Mittlerer Return on Investment
- **Gesamt ROI**: Kumulierter Return on Investment

### Risiko-Kennzahlen
- **Maximum Gain**: Höchster erzielter Gewinn
- **Maximum Loss**: Höchster erlittener Verlust
- **Volatilität**: Standardabweichung der Returns
- **Sharpe Ratio**: Risiko-adjustierte Performance
- **Win/Loss Ratio**: Verhältnis von Gewinnen zu Verlusten

## 🔧 Konfiguration

### Umgebungsvariablen (.env)
```env
# Google Sheets API
GOOGLE_CREDENTIALS={"type": "service_account", ...}

# Telegram Bot (für Alerts)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Alert-Schwellenwerte
In `automated_performance_monitor.py` anpassbar:
```python
self.alert_thresholds = {
    'min_success_rate': 40.0,      # Minimum Erfolgsrate in %
    'max_loss_threshold': -20.0,   # Maximum Verlust in %
    'min_signals_for_analysis': 5  # Minimum Anzahl Signale
}
```

## 📋 Beispiel-Report

```
📊 TRADING STRATEGY PERFORMANCE REPORT
════════════════════════════════════════════════════════════
📅 Generiert am: 2025-08-22 23:15:00

🎯 GESAMTPERFORMANCE
══════════════════════════════
📈 Gesamte Signale: 25
✅ Erfolgreiche Signale: 18
📊 Erfolgsrate: 72.0%
💰 Durchschnittlicher ROI: +3.2%
📈 Gesamt ROI: +80.5%
⏱️ Durchschnittliche Haltedauer: 2.3 Tage

🎯 PERFORMANCE NACH SIGNAL-TYP
═══════════════════════════════════
📊 BUY:
   • Anzahl: 15
   • Erfolgsrate: 80.0%
   • Ø ROI: +4.1%
   • Gesamt ROI: +61.5%

📊 SELL:
   • Anzahl: 10
   • Erfolgsrate: 60.0%
   • Ø ROI: +1.9%
   • Gesamt ROI: +19.0%
```

## 🔄 Integration mit Hauptsystem

### Google Sheets Spalten
Das System erwartet diese Spalten in der Google Sheets:
- `Strategy_Signal`: BUY/SELL/HOLD
- `Confidence_Score`: 0.0-1.0
- `Strategy_Reasoning`: Begründung für das Signal
- `Strategy_Name`: Name der verwendeten Strategie
- `Signal_Price`: Preis zum Zeitpunkt des Signals
- `Signal_Timestamp`: Zeitstempel des Signals

### Automatische Datensammlung
Die Trading-Signale werden automatisch von `Test_script.py` in die Google Sheets gespeichert:
```python
# Trading-Signal generieren und speichern
trading_signal = generate_trading_signals(daten)
daten['strategy_signal'] = trading_signal['signal']
daten['strategy_confidence'] = trading_signal['confidence']
daten['strategy_reasoning'] = trading_signal['reasoning']
daten['strategy_name'] = trading_signal['strategy_name']

# In Google Sheets speichern
schreibe_in_google_sheet(daten)
```

## 📈 Erweiterte Analyse

### CSV-Export für Excel/Python
```bash
python automated_performance_monitor.py export
# Erstellt: trading_signals_export_YYYYMMDD.csv
```

### Performance-Historie
Das System speichert eine Historie der Performance-Metriken:
```python
# In automated_performance_monitor.py
self.performance_history = [
    {
        'timestamp': datetime,
        'metrics': performance_dict
    }
]
```

## 🚨 Alert-System

### Automatische Warnungen
- **Niedrige Erfolgsrate**: < 40%
- **Hohe Verluste**: > 20%
- **Schlechte High-Confidence Signale**: Hohe Konfidenz aber niedrige Erfolgsrate

### Telegram-Benachrichtigungen
```
🚨 Performance Alerts

🔴 Niedrige Erfolgsrate: 35.2% (< 40.0%)
⚠️ Hoher Verlust detektiert: -22.1% (< -20.0%)
🔴 Very High (70-100%) Konfidenz-Signale haben nur 45.0% Erfolgsrate!
```

## 🛠️ Troubleshooting

### Häufige Probleme

1. **"Keine Trading-Signale gefunden"**
   - Lösung: Erst `Test_script.py` ausführen, um Signale zu generieren

2. **Google Sheets API Fehler**
   - Lösung: `GOOGLE_CREDENTIALS` in `.env` überprüfen

3. **Telegram-Alerts funktionieren nicht**
   - Lösung: `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` prüfen

### Debug-Modus
```bash
# Verbose Output für Debugging
python -u performance_tracker.py
```

## 📚 Weitere Entwicklung

### Geplante Features
- **Backtesting**: Historische Performance-Simulation
- **Machine Learning**: Optimierung der Trading-Strategien
- **Web-Dashboard**: Browser-basierte Performance-Anzeige
- **Multi-Exchange**: Support für mehrere Börsen

### Beiträge
Verbesserungsvorschläge und Pull Requests sind willkommen!
