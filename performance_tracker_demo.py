#!/usr/bin/env python3
"""
📊 Trading Strategy Performance Tracker - DEMO VERSION
=====================================================

Demo-Version für lokale Tests ohne Google Sheets Verbindung.
Verwendet demo_trading_data.json für Testzwecke.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

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
    
class PerformanceTrackerDemo:
    """Demo-Version des Performance Trackers mit lokalen Daten"""
    
    def __init__(self):
        self.sheet_data = None
        self.processed_signals = []
        self.performance_summary = {}
        
    def load_demo_data(self) -> bool:
        """Lädt Demo-Daten aus JSON-Datei"""
        try:
            if not os.path.exists('demo_trading_data.json'):
                print("❌ Demo-Daten nicht gefunden! Führen Sie zuerst create_demo_data.py aus.")
                return False
                
            with open('demo_trading_data.json', 'r', encoding='utf-8') as f:
                demo_data = json.load(f)
            
            self.sheet_data = pd.DataFrame(demo_data)
            
            print(f"✅ {len(self.sheet_data)} Demo-Datensätze geladen")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Laden der Demo-Daten: {e}")
            return False
    
    def analyze_signals(self) -> List[TradingSignalResult]:
        """Analysiert Trading-Signale und berechnet Performance"""
        if self.sheet_data is None or self.sheet_data.empty:
            print("❌ Keine Daten zum Analysieren verfügbar!")
            return []
        
        # Filtere nur Zeilen mit Trading-Signalen
        signal_data = self.sheet_data[
            (self.sheet_data['Strategy_Signal'].notna()) & 
            (self.sheet_data['Strategy_Signal'] != '') &
            (self.sheet_data['Strategy_Signal'] != 'HOLD')
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
            coin_signals['Signal_Timestamp'] = pd.to_datetime(coin_signals['Signal_Timestamp'])
            coin_signals = coin_signals.sort_values('Signal_Timestamp')
            
            for _, signal_row in coin_signals.iterrows():
                try:
                    signal_time = signal_row['Signal_Timestamp']
                    signal_price = float(signal_row['Signal_Price'])
                    current_price = float(signal_row['Preis_EUR'])
                    current_time = signal_row['Zeitstempel']
                    
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
    
    def analyze_performance_by_timeframes(self) -> Dict:
        """Analysiert Performance nach spezifischen Zeiträumen (Tage/Wochen/Monate)"""
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
        
        timeframe_analysis = {}
        
        # 1. Performance nach Haltedauer-Kategorien
        timeframe_analysis['by_holding_period'] = {}
        
        # Kategorisiere nach Haltedauer
        def categorize_holding_period(days):
            if days <= 7:
                return 'Kurzfristig (1-7 Tage)'
            elif days <= 30:
                return 'Mittelfristig (8-30 Tage)'
            else:
                return 'Langfristig (31+ Tage)'
        
        signals_df['period_category'] = signals_df['holding_period_days'].apply(categorize_holding_period)
        
        for category in signals_df['period_category'].unique():
            subset = signals_df[signals_df['period_category'] == category]
            timeframe_analysis['by_holding_period'][category] = {
                'count': len(subset),
                'success_rate': (subset['successful'].sum() / len(subset)) * 100 if len(subset) > 0 else 0,
                'average_roi': subset['roi_percent'].mean(),
                'total_roi': subset['roi_percent'].sum(),
                'average_holding_days': subset['holding_period_days'].mean()
            }
        
        # 2. Rolling Performance Windows (Wöchentlich/Monatlich)
        signals_df_sorted = signals_df.sort_values('signal_timestamp')
        
        # Wöchentliche Performance
        signals_df_sorted['week'] = signals_df_sorted['signal_timestamp'].dt.to_period('W')
        weekly_performance = signals_df_sorted.groupby('week').agg({
            'roi_percent': ['mean', 'sum', 'count'],
            'successful': 'sum'
        }).round(2)
        
        if not weekly_performance.empty:
            timeframe_analysis['weekly_performance'] = {
                'best_week': {
                    'period': str(weekly_performance['roi_percent']['sum'].idxmax()),
                    'total_roi': weekly_performance['roi_percent']['sum'].max(),
                    'signals_count': int(weekly_performance['roi_percent']['count'].loc[weekly_performance['roi_percent']['sum'].idxmax()])
                },
                'worst_week': {
                    'period': str(weekly_performance['roi_percent']['sum'].idxmin()),
                    'total_roi': weekly_performance['roi_percent']['sum'].min(),
                    'signals_count': int(weekly_performance['roi_percent']['count'].loc[weekly_performance['roi_percent']['sum'].idxmin()])
                },
                'average_weekly_roi': weekly_performance['roi_percent']['mean'].mean()
            }
        
        # Monatliche Performance
        signals_df_sorted['month'] = signals_df_sorted['signal_timestamp'].dt.to_period('M')
        monthly_performance = signals_df_sorted.groupby('month').agg({
            'roi_percent': ['mean', 'sum', 'count'],
            'successful': 'sum'
        }).round(2)
        
        if not monthly_performance.empty:
            timeframe_analysis['monthly_performance'] = {
                'best_month': {
                    'period': str(monthly_performance['roi_percent']['sum'].idxmax()),
                    'total_roi': monthly_performance['roi_percent']['sum'].max(),
                    'signals_count': int(monthly_performance['roi_percent']['count'].loc[monthly_performance['roi_percent']['sum'].idxmax()])
                },
                'worst_month': {
                    'period': str(monthly_performance['roi_percent']['sum'].idxmin()),
                    'total_roi': monthly_performance['roi_percent']['sum'].min(),
                    'signals_count': int(monthly_performance['roi_percent']['count'].loc[monthly_performance['roi_percent']['sum'].idxmin()])
                },
                'average_monthly_roi': monthly_performance['roi_percent']['mean'].mean()
            }
        
        # 3. Kumulative Performance und Trend-Analyse
        signals_df_sorted['cumulative_roi'] = signals_df_sorted['roi_percent'].cumsum()
        signals_df_sorted['rolling_avg_7'] = signals_df_sorted['roi_percent'].rolling(window=7, min_periods=1).mean()
        signals_df_sorted['rolling_avg_30'] = signals_df_sorted['roi_percent'].rolling(window=30, min_periods=1).mean()
        
        # Trend-Analyse (letzten 10 vs. ersten 10 Signale)
        if len(signals_df_sorted) >= 20:
            recent_performance = signals_df_sorted.tail(10)['roi_percent'].mean()
            early_performance = signals_df_sorted.head(10)['roi_percent'].mean()
            improving_trend = recent_performance > early_performance
        else:
            recent_performance = signals_df_sorted['roi_percent'].mean()
            early_performance = signals_df_sorted['roi_percent'].mean()
            improving_trend = None
        
        timeframe_analysis['trend_analysis'] = {
            'recent_avg_roi': recent_performance,
            'early_avg_roi': early_performance,
            'improving_trend': improving_trend,
            'current_cumulative_roi': signals_df_sorted['cumulative_roi'].iloc[-1] if not signals_df_sorted.empty else 0,
            'best_cumulative_roi': signals_df_sorted['cumulative_roi'].max() if not signals_df_sorted.empty else 0,
            'worst_drawdown': (signals_df_sorted['cumulative_roi'] - signals_df_sorted['cumulative_roi'].cummax()).min() if not signals_df_sorted.empty else 0
        }
        
        # 4. Win/Loss Streaks
        signals_df_sorted['win_streak'] = (signals_df_sorted['successful'] == True).groupby((signals_df_sorted['successful'] != signals_df_sorted['successful'].shift()).cumsum()).cumsum()
        signals_df_sorted['loss_streak'] = (signals_df_sorted['successful'] == False).groupby((signals_df_sorted['successful'] != signals_df_sorted['successful'].shift()).cumsum()).cumsum()
        
        timeframe_analysis['streaks'] = {
            'max_win_streak': signals_df_sorted['win_streak'].max() if not signals_df_sorted.empty else 0,
            'max_loss_streak': signals_df_sorted['loss_streak'].max() if not signals_df_sorted.empty else 0,
            'current_streak': 'Win' if signals_df_sorted['successful'].iloc[-1] else 'Loss' if not signals_df_sorted.empty else 'N/A'
        }
        
        return timeframe_analysis
    
    def generate_enhanced_report(self) -> str:
        """Generiert einen erweiterten Performance-Report mit Zeitframe-Analyse"""
        basic_report = self.generate_report()
        
        if not self.processed_signals:
            return basic_report
        
        timeframe_data = self.analyze_performance_by_timeframes()
        
        # Erweitere den Report um Zeitframe-Analyse
        enhanced_section = f"""

📊 ERWEITERTE ZEITFRAME-ANALYSE (DEMO)
{'='*45}

⏱️ PERFORMANCE NACH HALTEDAUER
{'='*35}"""
        
        for period, data in timeframe_data.get('by_holding_period', {}).items():
            enhanced_section += f"""
📈 {period}:
   • Anzahl Signale: {data['count']}
   • Erfolgsrate: {data['success_rate']:.1f}%
   • Ø ROI: {data['average_roi']:.2f}%
   • Gesamt ROI: {data['total_roi']:.2f}%
   • Ø Haltedauer: {data['average_holding_days']:.1f} Tage"""
        
        # Wöchentliche Performance
        weekly = timeframe_data.get('weekly_performance', {})
        if weekly:
            enhanced_section += f"""

📅 WÖCHENTLICHE PERFORMANCE
{'='*30}
🏆 Beste Woche: {weekly['best_week']['period']} 
   └─ ROI: {weekly['best_week']['total_roi']:+.2f}% ({weekly['best_week']['signals_count']} Signale)
📉 Schlechteste Woche: {weekly['worst_week']['period']}
   └─ ROI: {weekly['worst_week']['total_roi']:+.2f}% ({weekly['worst_week']['signals_count']} Signale)
📊 Ø Wöchentliche ROI: {weekly['average_weekly_roi']:.2f}%"""
        
        # Monatliche Performance
        monthly = timeframe_data.get('monthly_performance', {})
        if monthly:
            enhanced_section += f"""

📅 MONATLICHE PERFORMANCE
{'='*30}
🏆 Bester Monat: {monthly['best_month']['period']}
   └─ ROI: {monthly['best_month']['total_roi']:+.2f}% ({monthly['best_month']['signals_count']} Signale)
📉 Schlechtester Monat: {monthly['worst_month']['period']}
   └─ ROI: {monthly['worst_month']['total_roi']:+.2f}% ({monthly['worst_month']['signals_count']} Signale)
📊 Ø Monatliche ROI: {monthly['average_monthly_roi']:.2f}%"""
        
        # Trend-Analyse
        trend = timeframe_data.get('trend_analysis', {})
        enhanced_section += f"""

📈 TREND-ANALYSE
{'='*20}
🎯 Aktuelle Kumulative ROI: {trend['current_cumulative_roi']:.2f}%
🚀 Beste Kumulative ROI: {trend['best_cumulative_roi']:.2f}%
📉 Maximaler Drawdown: {trend['worst_drawdown']:.2f}%
📊 Frühe Performance (Ø): {trend['early_avg_roi']:.2f}%
📊 Aktuelle Performance (Ø): {trend['recent_avg_roi']:.2f}%"""
        
        if trend['improving_trend'] is not None:
            trend_emoji = "📈" if trend['improving_trend'] else "📉"
            trend_text = "VERBESSERND" if trend['improving_trend'] else "VERSCHLECHTERND"
            enhanced_section += f"\n{trend_emoji} Trend: {trend_text}"
        
        # Win/Loss Streaks
        streaks = timeframe_data.get('streaks', {})
        enhanced_section += f"""

🏃‍♂️ WIN/LOSS STREAKS
{'='*25}
🔥 Längste Gewinnserie: {streaks['max_win_streak']} Signale
❄️ Längste Verlustserie: {streaks['max_loss_streak']} Signale
📊 Aktuelle Serie: {streaks['current_streak']}"""
        
        # Performance-Warnungen
        enhanced_section += f"""

⚠️ PERFORMANCE-WARNUNGEN
{'='*30}"""
        
        warnings = []
        if trend.get('improving_trend') == False:
            warnings.append("🔴 Performance-Trend verschlechtert sich!")
        if trend.get('worst_drawdown', 0) < -20:
            warnings.append(f"🔴 Hoher Drawdown: {trend['worst_drawdown']:.1f}%")
        if streaks.get('max_loss_streak', 0) > 5:
            warnings.append(f"🔴 Lange Verlustserie: {streaks['max_loss_streak']} Signale")
        
        if warnings:
            for warning in warnings:
                enhanced_section += f"\n{warning}"
        else:
            enhanced_section += "\n✅ Keine kritischen Performance-Warnungen"
        
        enhanced_section += f"""

🎯 DEMO-MODUS AKTIV
{'='*25}
Diese Analyse basiert auf simulierten Demo-Daten.
Für Live-Daten konfigurieren Sie Google Sheets Credentials.
"""
        
        return basic_report + enhanced_section
    
    def generate_report(self) -> str:
        """Generiert einen detaillierten Performance-Report"""
        if not self.performance_summary:
            return "❌ Keine Performance-Daten verfügbar. Führen Sie zuerst die Analyse durch."
        
        metrics = self.performance_summary
        
        report = f"""
📊 TRADING STRATEGY PERFORMANCE REPORT (DEMO)
{'='*65}
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
        
        report += "\n📈 TOP PERFORMER:"
        for coin, data in coin_performance[:3]:
            report += f"""
   • {coin}: {data['total_roi']:+.2f}% ROI ({data['count']} Signale, {data['success_rate']:.1f}% Erfolg)"""
        
        if len(coin_performance) > 3:
            report += "\n📉 WORST PERFORMER:"
            for coin, data in coin_performance[-2:]:
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

{'='*65}
📊 Demo Report Ende
"""
        
        return report

def main():
    """Hauptfunktion für Demo Performance-Tracking"""
    print("🚀 Trading Strategy Performance Tracker - DEMO VERSION")
    print("=" * 60)
    
    tracker = PerformanceTrackerDemo()
    
    # Lade Demo-Daten
    print("📡 Lade Demo-Daten...")
    if not tracker.load_demo_data():
        print("❌ Fehler beim Laden der Demo-Daten. Script wird beendet.")
        return
    
    # Analysiere Signale
    print("📊 Analysiere Trading-Signale...")
    signals = tracker.analyze_signals()
    
    if not signals:
        print("❌ Keine Trading-Signale zum Analysieren gefunden.")
        return
    
    # Berechne Performance
    print("📈 Berechne Performance-Metriken...")
    metrics = tracker.calculate_performance_metrics()
    
    # Generiere und zeige Report
    print("📋 Generiere erweiterten Performance-Report...")
    report = tracker.generate_enhanced_report()
    print(report)
    
    # Speichere Report
    filename = f"demo_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ Demo-Report gespeichert: {filename}")
    except Exception as e:
        print(f"❌ Fehler beim Speichern: {e}")
    
    print(f"\n🎉 Demo Performance-Analyse abgeschlossen!")

if __name__ == "__main__":
    main()
