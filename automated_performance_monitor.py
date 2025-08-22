#!/usr/bin/env python3
"""
📊 Automated Trading Performance Monitor
========================================

Automatisches Monitoring-System für Trading-Signal Performance.
Läuft kontinuierlich und erstellt regelmäßige Reports.

Features:
- Kontinuierliche Performance-Überwachung
- Automatische Report-Generierung
- Telegram-Benachrichtigungen bei wichtigen Events
- CSV-Export für weitere Analyse
- Dashboard-Integration

Autor: AI Assistant
Datum: 2025-08-22
Version: 1.0
"""

import os
import sys
import time
import json
import schedule
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import requests
from performance_tracker import PerformanceTracker
from dotenv import load_dotenv

# .env Datei laden
load_dotenv()

class PerformanceMonitor:
    """Automatisches Performance-Monitoring System"""
    
    def __init__(self):
        self.tracker = PerformanceTracker()
        self.last_report_time = None
        self.performance_history = []
        self.alert_thresholds = {
            'min_success_rate': 40.0,  # Minimum Erfolgsrate in %
            'max_loss_threshold': -20.0,  # Maximum Verlust in %
            'min_signals_for_analysis': 5  # Minimum Anzahl Signale für Analyse
        }
    
    def send_telegram_alert(self, message: str) -> bool:
        """Sendet eine Telegram-Benachrichtigung"""
        try:
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not bot_token or not chat_id:
                print("⚠️ Telegram-Credentials nicht konfiguriert")
                return False
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Fehler beim Senden der Telegram-Nachricht: {e}")
            return False
    
    def check_performance_alerts(self, metrics: Dict) -> List[str]:
        """Prüft auf Performance-Alerts und gibt Warnungen zurück"""
        alerts = []
        
        # Erfolgsrate prüfen
        if metrics.get('success_rate_percent', 0) < self.alert_thresholds['min_success_rate']:
            alerts.append(f"🚨 Niedrige Erfolgsrate: {metrics['success_rate_percent']:.1f}% (< {self.alert_thresholds['min_success_rate']}%)")
        
        # Maximaler Verlust prüfen
        risk_metrics = metrics.get('risk_metrics', {})
        max_loss = risk_metrics.get('max_loss', 0)
        if max_loss < self.alert_thresholds['max_loss_threshold']:
            alerts.append(f"⚠️ Hoher Verlust detektiert: {max_loss:.2f}% (< {self.alert_thresholds['max_loss_threshold']}%)")
        
        # Prüfe auf schlechte Performance bei hoher Konfidenz
        by_confidence = metrics.get('by_confidence', {})
        for conf_level, data in by_confidence.items():
            if 'High' in conf_level or 'Very High' in conf_level:
                if data.get('success_rate', 0) < 50:
                    alerts.append(f"🔴 {conf_level} Konfidenz-Signale haben nur {data['success_rate']:.1f}% Erfolgsrate!")
        
        return alerts
    
    def generate_performance_summary(self, metrics: Dict) -> str:
        """Generiert eine kompakte Performance-Zusammenfassung"""
        if not metrics:
            return "❌ Keine Performance-Daten verfügbar"
        
        total_signals = metrics.get('total_signals', 0)
        success_rate = metrics.get('success_rate_percent', 0)
        total_roi = metrics.get('total_roi', 0)
        avg_roi = metrics.get('average_roi', 0)
        
        # Bestimme Performance-Status
        if success_rate >= 70:
            status_emoji = "🎉"
            status_text = "Exzellent"
        elif success_rate >= 50:
            status_emoji = "✅"
            status_text = "Gut"
        elif success_rate >= 40:
            status_emoji = "🟡"
            status_text = "Okay"
        else:
            status_emoji = "🔴"
            status_text = "Schlecht"
        
        summary = f"""
📊 <b>Trading Performance Update</b>
{status_emoji} Status: <b>{status_text}</b>

📈 <b>Statistiken:</b>
• Signale: {total_signals}
• Erfolgsrate: {success_rate:.1f}%
• Gesamt ROI: {total_roi:+.2f}%
• ⌀ ROI: {avg_roi:+.2f}%

🎯 <b>Nach Signal-Typ:</b>"""
        
        by_signal = metrics.get('by_signal_type', {})
        for signal_type, data in by_signal.items():
            summary += f"\n• {signal_type}: {data['success_rate']:.1f}% ({data['count']}x)"
        
        return summary
    
    def run_performance_check(self) -> bool:
        """Führt eine vollständige Performance-Prüfung durch"""
        try:
            print(f"🔄 Performance-Check gestartet: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Lade aktuelle Daten
            if not self.tracker.load_data_from_sheets():
                print("❌ Fehler beim Laden der Google Sheets Daten")
                return False
            
            # Analysiere Signale
            signals = self.tracker.analyze_signals()
            if len(signals) < self.alert_thresholds['min_signals_for_analysis']:
                print(f"⚠️ Zu wenige Signale für Analyse: {len(signals)} < {self.alert_thresholds['min_signals_for_analysis']}")
                return False
            
            # Berechne Metriken
            metrics = self.tracker.calculate_performance_metrics()
            
            # Speichere in History
            self.performance_history.append({
                'timestamp': datetime.now(),
                'metrics': metrics.copy()
            })
            
            # Prüfe Alerts
            alerts = self.check_performance_alerts(metrics)
            
            # Sende Alerts falls nötig
            if alerts:
                alert_message = "🚨 <b>Performance Alerts</b>\n\n" + "\n".join(alerts)
                self.send_telegram_alert(alert_message)
                print(f"🚨 {len(alerts)} Performance-Alerts gesendet")
            
            print(f"✅ Performance-Check abgeschlossen: {metrics['success_rate_percent']:.1f}% Erfolgsrate")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Performance-Check: {e}")
            return False
    
    def generate_daily_report(self):
        """Generiert einen täglichen Performance-Report"""
        try:
            print("📊 Generiere täglichen Performance-Report...")
            
            if not self.tracker.load_data_from_sheets():
                return
            
            signals = self.tracker.analyze_signals()
            if not signals:
                print("❌ Keine Signale für täglichen Report")
                return
            
            metrics = self.tracker.calculate_performance_metrics()
            
            # Erstelle Telegram-Summary
            summary = self.generate_performance_summary(metrics)
            summary += f"\n\n📅 Report vom: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            # Sende Telegram-Report
            if self.send_telegram_alert(summary):
                print("✅ Täglicher Report per Telegram gesendet")
            
            # Speichere detaillierten Report
            filename = self.tracker.save_report(f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt")
            
            # CSV Export für weitere Analyse
            self.export_to_csv()
            
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des täglichen Reports: {e}")
    
    def export_to_csv(self) -> str:
        """Exportiert Performance-Daten als CSV"""
        try:
            if not self.tracker.processed_signals:
                return ""
            
            # Konvertiere zu DataFrame
            data = []
            for signal in self.tracker.processed_signals:
                data.append({
                    'Timestamp': signal.signal_timestamp,
                    'Coin': signal.coin,
                    'Signal': signal.signal,
                    'Confidence': signal.confidence,
                    'Signal_Price': signal.signal_price,
                    'Current_Price': signal.current_price,
                    'ROI_Percent': signal.roi_percent,
                    'Holding_Period_Days': signal.holding_period_days,
                    'Strategy_Name': signal.strategy_name,
                    'Reasoning': signal.reasoning,
                    'Successful': signal.roi_percent > 0
                })
            
            df = pd.DataFrame(data)
            filename = f"trading_signals_export_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8')
            
            print(f"📄 CSV Export erstellt: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Fehler beim CSV-Export: {e}")
            return ""
    
    def start_monitoring(self):
        """Startet das kontinuierliche Monitoring"""
        print("🚀 Trading Performance Monitor gestartet")
        print("=" * 50)
        
        # Plane regelmäßige Tasks
        schedule.every(30).minutes.do(self.run_performance_check)
        schedule.every().day.at("09:00").do(self.generate_daily_report)
        schedule.every().day.at("18:00").do(self.generate_daily_report)
        
        # Initial Check
        self.run_performance_check()
        
        print("⏰ Geplante Tasks:")
        print("• Performance Check: Alle 30 Minuten")
        print("• Täglicher Report: 09:00 und 18:00 Uhr")
        print("\n🔄 Monitoring läuft... (Strg+C zum Beenden)")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring gestoppt")

def main():
    """Hauptfunktion"""
    print("🤖 Automated Trading Performance Monitor")
    print("=" * 50)
    
    monitor = PerformanceMonitor()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'check':
            # Einmaliger Performance-Check
            monitor.run_performance_check()
        elif command == 'report':
            # Einmaliger Report
            monitor.generate_daily_report()
        elif command == 'export':
            # CSV Export
            monitor.tracker.load_data_from_sheets()
            monitor.tracker.analyze_signals()
            monitor.export_to_csv()
        else:
            print(f"❌ Unbekannter Befehl: {command}")
            print("💡 Verfügbare Befehle: check, report, export")
    else:
        # Startet kontinuierliches Monitoring
        monitor.start_monitoring()

if __name__ == "__main__":
    main()
