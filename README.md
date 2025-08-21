# 🚀 Krypto-Analyse-Bot - Modulare Trading-Plattform

Eine **professionelle, modulare Krypto-Analyse- und Trading-Simulations-Plattform** mit KI-unterstützter News-Analyse, erweiterten technischen Indikatoren und automatisiertem Portfolio-Management.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 📋 **Projektübersicht**

### **Was ist neu in v2.0?**
- ✅ **Modulare Architektur** mit klarer Trennung der Verantwortlichkeiten
- ✅ **Multi-Strategy Framework** für verschiedene Handelsansätze  
- ✅ **Portfolio-Simulator** mit Backtesting-Funktionalität
- ✅ **ATR-basierte Volatilitäts-Analyse** und dynamische Stop-Loss-Berechnung
- ✅ **KI-verstärkte News-Analyse** mit Google Gemini API
- ✅ **Parallele Datenverarbeitung** für 6x bessere Performance
- ✅ **Umfassende Type Safety** mit Python dataclasses und Protocols

---

## 🏗️ **Architektur**

```
krypto-analyse-bot/
├── config.py                     # Zentrale Konfiguration
├── Test_script.py                # Legacy Script (backward compatible)
├── validate_migration.py         # Migrations-Validator
├── modules/
│   ├── data_models.py            # Type-safe Datenstrukturen
│   ├── core/
│   │   └── data_fetcher.py       # API-Abstraktionsschicht
│   ├── strategies/
│   │   ├── base_strategy.py      # Abstract Strategy Framework
│   │   └── conservative/
│   │       ├── config.py         # Strategy-spezifische Config
│   │       └── trend_strategy.py # Conservative Trend Following
│   ├── simulation/
│   │   └── portfolio_simulator.py # Portfolio & Backtesting
│   └── utils/
│       └── logger.py             # Erweiterte Logging-Infrastruktur
├── tests/
│   └── test_strategies.py        # Umfassende Test-Suite
└── logs/                         # Strukturierte Log-Files
```

Weitere Details siehe vollständige Dokumentation...
