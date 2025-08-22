#!/usr/bin/env python3
"""
📊 Trading Strategy Performance Tracker
========================================

Analysiert die Erfolgsrate der Trading-Empfehlungen aus der Google Sheets Datenbank.
Dieses Skript evaluiert:

1. Erfolgsrate von BUY/SELL/HOLD Signalen
2. ROI (Return on Investment) pro Signal
3. Präzision und Recall der Strategien
4. Zeitbasierte Performance-Analyse
5. Risiko-adjustierte Returns

Autor: AI Assistant
Datum: 2025-08-22
Version: 1.0
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import gspread
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
from dotenv import load_dotenv

# .env Datei laden
load_dotenv()

@dataclass
class TradingSignalResult:
    """Repräsentiert das Ergebnis eines Trading-Signals"""
    coin: str
    signal: str  # BUY/SELL/HOLD
    confidence: float
    signal_price: float
    signal_timestamp: datetime
    current_price: float
    current_timestamp: datetime
    roi_percent: float
    holding_period_days: int
    strategy_name: str
    reasoning: str
    
class PerformanceTracker:
    """Analysiert Trading-Signal Performance aus Google Sheets"""
    
    def __init__(self):
        self.sheet_data = None
        self.processed_signals = []
        self.performance_summary = {}
        
    def load_data_from_sheets(self) -> bool:
        """Lädt Daten aus Google Sheets"""
        try:
            credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
            if not credentials_json_str:
                print("❌ GOOGLE_CREDENTIALS nicht in .env gefunden!")
                return False
                
            credentials_dict = json.loads(credentials_json_str)
            gc = gspread.service_account_from_dict(credentials_dict)
            spreadsheet = gc.open("Krypto-Analyse-DB")
            worksheet = spreadsheet.worksheet("Market_Data")
            
            # Alle Daten laden
            all_records = worksheet.get_all_records()
            self.sheet_data = pd.DataFrame(all_records)
            
            print(f"✅ {len(self.sheet_data)} Datensätze aus Google Sheets geladen")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Google Sheets: {e}")
            return False
    
    def analyze_signals(self) -> List[TradingSignalResult]:
        """Analysiert Trading-Signale und berechnet Performance"""
        if self.sheet_data is None or self.sheet_data.empty:
            print("❌ Keine Daten zum Analysieren verfügbar!")
            return []
        
        # Filtere nur Zeilen mit Trading-Signalen
        signal_data = self.sheet_data[
            (self.sheet_data.get('Strategy_Signal', '').notna()) & 
            (self.sheet_data.get('Strategy_Signal', '') != '') &
            (self.sheet_data.get('Strategy_Signal', '') != 'HOLD')
        ].copy()
        
        if signal_data.empty:
            print("❌ Keine Trading-Signale (BUY/SELL) in den Daten gefunden!")
            return []
        
        print(f"📊 Analysiere {len(signal_data)} Trading-Signale...")
        
        results = []
        
        # Gruppiere nach Coin und Signal
        for coin in signal_data['Coin_Name'].unique():
            coin_signals = signal_data[signal_data['Coin_Name'] == coin].copy()
            coin_signals['Zeitstempel'] = pd.to_datetime(coin_signals['Zeitstempel'])
            coin_signals = coin_signals.sort_values('Zeitstempel')
            
            for _, signal_row in coin_signals.iterrows():
                try:
                    # Finde das nächste Preisupdate nach dem Signal
                    signal_time = signal_row['Zeitstempel']
                    signal_price = float(signal_row['Signal_Price']) if 'Signal_Price' in signal_row else float(signal_row['Preis_EUR'])
                    
                    # Suche nach späteren Preisdaten für diesen Coin
                    later_data = self.sheet_data[
                        (self.sheet_data['Coin_Name'] == coin) &
                        (pd.to_datetime(self.sheet_data['Zeitstempel']) > signal_time)
                    ].copy()
                    
                    if not later_data.empty:
                        # Nehme den neuesten verfügbaren Preis
                        latest_data = later_data.sort_values('Zeitstempel').iloc[-1]
                        current_price = float(latest_data['Preis_EUR'])
                        current_time = pd.to_datetime(latest_data['Zeitstempel'])
                        
                        # Berechne ROI basierend auf Signal-Typ
                        signal_type = signal_row['Strategy_Signal']
                        if signal_type == 'BUY':
                            roi_percent = ((current_price - signal_price) / signal_price) * 100
                        elif signal_type == 'SELL':
                            roi_percent = ((signal_price - current_price) / signal_price) * 100
                        else:  # HOLD
                            roi_percent = 0.0
                        
                        holding_period = (current_time - signal_time).days
                        
                        result = TradingSignalResult(
                            coin=coin,
                            signal=signal_type,
                            confidence=float(signal_row.get('Confidence_Score', 0.5)),
                            signal_price=signal_price,
                            signal_timestamp=signal_time,
                            current_price=current_price,
                            current_timestamp=current_time,
                            roi_percent=roi_percent,
                            holding_period_days=holding_period,
                            strategy_name=signal_row.get('Strategy_Name', 'unknown'),
                            reasoning=signal_row.get('Strategy_Reasoning', '')
                        )
                        
                        results.append(result)
                        
                except Exception as e:
                    print(f"⚠️ Fehler bei Signal-Analyse für {coin}: {e}")
                    continue
        
        self.processed_signals = results
        print(f"✅ {len(results)} Trading-Signale erfolgreich analysiert")
        return results
    
    def calculate_performance_metrics(self) -> Dict:
        """Berechnet umfassende Performance-Metriken"""
        if not self.processed_signals:
            return {}
        
        signals_df = pd.DataFrame([
            {
                'coin': s.coin,
                'signal': s.signal,
                'confidence': s.confidence,
                'roi_percent': s.roi_percent,
                'holding_period_days': s.holding_period_days,
                'strategy_name': s.strategy_name,
                'signal_timestamp': s.signal_timestamp,
                'successful': s.roi_percent > 0
            }
            for s in self.processed_signals
        ])
        
        metrics = {}
        
        # Gesamtstatistiken
        total_signals = len(signals_df)
        successful_signals = signals_df['successful'].sum()
        success_rate = (successful_signals / total_signals) * 100 if total_signals > 0 else 0
        
        metrics['total_signals'] = total_signals
        metrics['successful_signals'] = successful_signals
        metrics['success_rate_percent'] = success_rate
        metrics['average_roi'] = signals_df['roi_percent'].mean()
        metrics['median_roi'] = signals_df['roi_percent'].median()
        metrics['total_roi'] = signals_df['roi_percent'].sum()
        metrics['average_holding_period'] = signals_df['holding_period_days'].mean()
        
        # Performance nach Signal-Typ
        metrics['by_signal_type'] = {}
        for signal_type in signals_df['signal'].unique():
            signal_subset = signals_df[signals_df['signal'] == signal_type]
            metrics['by_signal_type'][signal_type] = {
                'count': len(signal_subset),
                'success_rate': (signal_subset['successful'].sum() / len(signal_subset)) * 100 if len(signal_subset) > 0 else 0,
                'average_roi': signal_subset['roi_percent'].mean(),
                'total_roi': signal_subset['roi_percent'].sum()
            }
        
        # Performance nach Coin
        metrics['by_coin'] = {}
        for coin in signals_df['coin'].unique():
            coin_subset = signals_df[signals_df['coin'] == coin]
            metrics['by_coin'][coin] = {
                'count': len(coin_subset),
                'success_rate': (coin_subset['successful'].sum() / len(coin_subset)) * 100 if len(coin_subset) > 0 else 0,
                'average_roi': coin_subset['roi_percent'].mean(),
                'total_roi': coin_subset['roi_percent'].sum()
            }
        
        # Performance nach Konfidenz-Level
        metrics['by_confidence'] = {}
        confidence_bins = [0, 0.3, 0.5, 0.7, 1.0]
        confidence_labels = ['Low (0-30%)', 'Medium (30-50%)', 'High (50-70%)', 'Very High (70-100%)']
        
        signals_df['confidence_bin'] = pd.cut(signals_df['confidence'], bins=confidence_bins, labels=confidence_labels, include_lowest=True)
        
        for conf_level in signals_df['confidence_bin'].unique():
            if pd.notna(conf_level):
                conf_subset = signals_df[signals_df['confidence_bin'] == conf_level]
                metrics['by_confidence'][str(conf_level)] = {
                    'count': len(conf_subset),
                    'success_rate': (conf_subset['successful'].sum() / len(conf_subset)) * 100 if len(conf_subset) > 0 else 0,
                    'average_roi': conf_subset['roi_percent'].mean(),
                    'total_roi': conf_subset['roi_percent'].sum()
                }
        
        # Risiko-Metriken
        positive_returns = signals_df[signals_df['roi_percent'] > 0]['roi_percent']
        negative_returns = signals_df[signals_df['roi_percent'] < 0]['roi_percent']
        
        metrics['risk_metrics'] = {
            'max_gain': signals_df['roi_percent'].max(),
            'max_loss': signals_df['roi_percent'].min(),
            'volatility': signals_df['roi_percent'].std(),
            'sharpe_ratio': signals_df['roi_percent'].mean() / signals_df['roi_percent'].std() if signals_df['roi_percent'].std() > 0 else 0,
            'win_loss_ratio': positive_returns.mean() / abs(negative_returns.mean()) if len(negative_returns) > 0 and negative_returns.mean() < 0 else float('inf')
        }
        
        self.performance_summary = metrics
        return metrics
    
    def generate_report(self) -> str:
        """Generiert einen detaillierten Performance-Report"""
        if not self.performance_summary:
            return "❌ Keine Performance-Daten verfügbar. Führen Sie zuerst die Analyse durch."
        
        metrics = self.performance_summary
        
        report = f"""
📊 TRADING STRATEGY PERFORMANCE REPORT
{'='*60}
📅 Generiert am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 GESAMTPERFORMANCE
{'='*30}
📈 Gesamte Signale: {metrics['total_signals']}
✅ Erfolgreiche Signale: {metrics['successful_signals']}
📊 Erfolgsrate: {metrics['success_rate_percent']:.1f}%
💰 Durchschnittlicher ROI: {metrics['average_roi']:.2f}%
📈 Gesamt ROI: {metrics['total_roi']:.2f}%
⏱️ Durchschnittliche Haltedauer: {metrics['average_holding_period']:.1f} Tage

🎯 PERFORMANCE NACH SIGNAL-TYP
{'='*35}"""
        
        for signal_type, data in metrics['by_signal_type'].items():
            report += f"""
📊 {signal_type}:
   • Anzahl: {data['count']}
   • Erfolgsrate: {data['success_rate']:.1f}%
   • Ø ROI: {data['average_roi']:.2f}%
   • Gesamt ROI: {data['total_roi']:.2f}%"""
        
        report += f"""

🪙 TOP/WORST PERFORMING COINS
{'='*35}"""
        
        # Sortiere Coins nach Gesamt-ROI
        coin_performance = sorted(metrics['by_coin'].items(), key=lambda x: x[1]['total_roi'], reverse=True)
        
        report += "\n📈 TOP 5 PERFORMER:"
        for coin, data in coin_performance[:5]:
            report += f"""
   • {coin}: {data['total_roi']:+.2f}% ROI ({data['count']} Signale, {data['success_rate']:.1f}% Erfolg)"""
        
        if len(coin_performance) > 5:
            report += "\n📉 WORST 3 PERFORMER:"
            for coin, data in coin_performance[-3:]:
                report += f"""
   • {coin}: {data['total_roi']:+.2f}% ROI ({data['count']} Signale, {data['success_rate']:.1f}% Erfolg)"""
        
        report += f"""

🎯 KONFIDENZ-LEVEL ANALYSE
{'='*30}"""
        
        for conf_level, data in metrics['by_confidence'].items():
            report += f"""
📊 {conf_level}:
   • Anzahl: {data['count']}
   • Erfolgsrate: {data['success_rate']:.1f}%
   • Ø ROI: {data['average_roi']:.2f}%"""
        
        risk_metrics = metrics['risk_metrics']
        report += f"""

⚠️ RISIKO-ANALYSE
{'='*20}
🚀 Max Gewinn: {risk_metrics['max_gain']:.2f}%
📉 Max Verlust: {risk_metrics['max_loss']:.2f}%
📊 Volatilität: {risk_metrics['volatility']:.2f}%
📈 Sharpe Ratio: {risk_metrics['sharpe_ratio']:.3f}
💪 Gewinn/Verlust Ratio: {risk_metrics['win_loss_ratio']:.2f}

💡 EMPFEHLUNGEN
{'='*20}"""
        
        # Generiere automatische Empfehlungen
        if metrics['success_rate_percent'] >= 70:
            report += "\n✅ Ausgezeichnete Performance! Die Strategie funktioniert sehr gut."
        elif metrics['success_rate_percent'] >= 50:
            report += "\n🟡 Solide Performance. Optimierungspotential vorhanden."
        else:
            report += "\n🔴 Performance unter Erwartung. Strategie überdenken!"
        
        if risk_metrics['sharpe_ratio'] > 1.0:
            report += "\n📈 Gutes Risiko-Rendite-Verhältnis."
        else:
            report += "\n⚠️ Risiko-Rendite-Verhältnis könnte besser sein."
        
        report += f"""

{'='*60}
📊 Report Ende
"""
        
        return report
    
    def save_report(self, filename: str = None) -> str:
        """Speichert den Report in eine Datei"""
        if filename is None:
            filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        report_content = self.generate_report()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"✅ Performance-Report gespeichert: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Fehler beim Speichern des Reports: {e}")
            return ""

def main():
    """Hauptfunktion für Performance-Tracking"""
    print("🚀 Trading Strategy Performance Tracker")
    print("=" * 50)
    
    tracker = PerformanceTracker()
    
    # Lade Daten
    print("📡 Lade Daten aus Google Sheets...")
    if not tracker.load_data_from_sheets():
        print("❌ Fehler beim Laden der Daten. Script wird beendet.")
        return
    
    # Analysiere Signale
    print("📊 Analysiere Trading-Signale...")
    signals = tracker.analyze_signals()
    
    if not signals:
        print("❌ Keine Trading-Signale zum Analysieren gefunden.")
        print("💡 Tipp: Führen Sie erst den Test_script.py aus, um Trading-Signale zu generieren.")
        return
    
    # Berechne Performance
    print("📈 Berechne Performance-Metriken...")
    metrics = tracker.calculate_performance_metrics()
    
    # Generiere und zeige Report
    print("📋 Generiere Performance-Report...")
    report = tracker.generate_report()
    print(report)
    
    # Speichere Report
    filename = tracker.save_report()
    
    print(f"\n🎉 Performance-Analyse abgeschlossen!")
    print(f"📄 Report gespeichert als: {filename}")

if __name__ == "__main__":
    main()
