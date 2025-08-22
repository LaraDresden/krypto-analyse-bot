# 🚀 Krypto-Analyse-Bot - Lauffähiger Code Setup

## ⚡ Schnellstart

### 1. **Credentials konfigurieren**

Bearbeiten Sie die `.env` Datei und ersetzen Sie die Platzhalter:

```bash
# Bitvavo API
BITVAVO_API_KEY=ihr_echter_bitvavo_api_key
BITVAVO_API_SECRET=ihr_echter_bitvavo_api_secret

# Google Gemini API
GEMINI_API_KEY=ihr_echter_gemini_api_key

# News API
NEWS_API_KEY=ihr_echter_news_api_key

# Telegram Bot
TELEGRAM_BOT_TOKEN=ihr_echter_telegram_bot_token
TELEGRAM_CHAT_ID=ihre_echte_telegram_chat_id

# Google Credentials (JSON als einzeilige String)
GOOGLE_CREDENTIALS={"type":"service_account","project_id":"..."}
GOOGLE_SHEETS_ID=ihre_google_sheets_id
```

### 2. **Dependencies installieren**

```powershell
pip install pandas numpy requests gspread google-auth python-dotenv ccxt
```

### 3. **System testen**

```powershell
python integration_test.py
```

### 4. **Backend ausführen**

```powershell
python Test_script.py
```

### 5. **Frontend öffnen**

Öffnen Sie `index_v2.1.2.html` in einem Browser.

---

## 📋 Systemkomponenten

### **Backend** (`Test_script.py`)
- ✅ Crypto-Marktdaten von Bitvavo API
- ✅ KI-Analyse mit Google Gemini
- ✅ Trading-Signal-Generierung
- ✅ Google Sheets Integration
- ✅ Telegram-Benachrichtigungen

### **Performance Tracking** (`performance_tracker.py`)
- ✅ Timeframe-basierte Analyse (kurz/mittel/lang)
- ✅ Erfolgsrate-Berechnung
- ✅ Google Sheets Datenquelle
- ✅ Detaillierte Berichte

### **Frontend** (`index_v2.1.2.html`)
- ✅ Live-Dashboard mit Chart.js
- ✅ Google Sheets Integration
- ✅ Demo-Daten Fallback
- ✅ Responsive Design
- ✅ Trading-Signal-Anzeige

---

## 🔧 Fehlerbehebung

### **"GOOGLE_CREDENTIALS nicht gefunden"**
- Stellen Sie sicher, dass die JSON-Credentials als **einzeilige String** in der .env Datei stehen
- Keine Zeilumbrüche im JSON!

### **"Spreadsheet not found"**
- Prüfen Sie die `GOOGLE_SHEETS_ID` in der .env Datei
- Stellen Sie sicher, dass der Service Account Zugriff auf das Sheet hat

### **Frontend zeigt nur Demo-Daten**
- Überprüfen Sie die Google Sheets URL im Frontend
- Stellen Sie sicher, dass das Sheet öffentlich lesbar ist oder verwenden Sie die API

### **Trading-Signale werden nicht generiert**
- Prüfen Sie die Bitvavo API Credentials
- Stellen Sie sicher, dass genügend Marktdaten verfügbar sind

---

## 📊 Demo-Modus

Für Tests ohne echte API-Keys:

```powershell
# Erstelle realistische Demo-Daten
python create_realistic_demo.py

# Nutze Performance Tracker Demo
python performance_tracker_demo.py
```

---

## 🎯 Erwartete Ausgabe

**Backend erfolgreich:**
```
✅ Trading-Strategien erfolgreich initialisiert
🚀 Starte SUPER-CHARGED KI-verstärkten Analyse-Lauf...
💰 Portfolio Gesamtwert: €275.15
🎯 BNB BUY Signal (75% Confidence)
📱 Telegram-Benachrichtigung erfolgreich gesendet!
```

**Frontend erfolgreich:**
```
✅ Live-Daten (grün) - Verbunden mit Google Sheets
🎮 Demo-Modus (gelb) - Fallback zu Demo-Daten
```

---

## 📈 Performance Tracking

Das System analysiert automatisch:
- **Kurzzeitige Performance** (< 1 Tag)
- **Mittelfristige Performance** (1-7 Tage) 
- **Langfristige Performance** (> 7 Tage)
- **Erfolgsraten** nach Timeframes
- **Gewinn/Verlust-Streaks**

---

## 🔐 Sicherheit

⚠️ **WICHTIG**: Die `.env` Datei enthält **Platzhalter** - keine echten Credentials!

Für Produktionsnutzung:
1. Echte API-Keys eintragen
2. `.env` zu `.gitignore` hinzufügen
3. Service Account Berechtigungen minimal halten

---

## 💡 Tipps

- Verwenden Sie `integration_test.py` vor dem ersten Start
- Prüfen Sie regelmäßig die Google Sheets Verbindung
- Telegram-Bot für Live-Updates konfigurieren
- Performance-Berichte für Trading-Optimierung nutzen
