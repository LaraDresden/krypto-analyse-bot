#!/usr/bin/env python3
"""
🚀 SUPER-CHARGED Krypto-Analyse Demo mit Live Google Sheets Integration
Erstellt realistische Demo-Daten für Performance-Testing
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def create_realistic_demo_data():
    """Erstellt realistische Demo-Daten für 50 Trading-Signale"""
    
    # Basis-Coins für Demo
    coins = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'LINK', 'AVAX', 'DOGE', 'XRP']
    
    # Zeitraum: Letzte 30 Tage
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    demo_signals = []
    
    for i in range(50):
        # Zufälliger Zeitpunkt in den letzten 30 Tagen
        signal_time = start_date + timedelta(
            seconds=random.randint(0, int((end_date - start_date).total_seconds()))
        )
        
        coin = random.choice(coins)
        signal_type = random.choice(['BUY', 'SELL'])
        
        # Realistische Preise (vereinfacht)
        price_ranges = {
            'BTC': (90000, 105000), 'ETH': (3500, 4500), 'BNB': (600, 800),
            'ADA': (0.7, 1.2), 'SOL': (150, 200), 'DOT': (8, 12),
            'LINK': (20, 30), 'AVAX': (35, 50), 'DOGE': (0.15, 0.25), 'XRP': (2.3, 2.8)
        }
        
        signal_price = round(random.uniform(*price_ranges[coin]), 4)
        
        # Aktueller Preis (simuliert) - 70% der Zeit profitabel
        if random.random() < 0.7:  # 70% Erfolgsrate
            if signal_type == 'BUY':
                current_price = signal_price * random.uniform(1.01, 1.15)  # 1-15% Gewinn
            else:  # SELL
                current_price = signal_price * random.uniform(0.85, 0.99)  # 1-15% Gewinn
        else:  # 30% Verluste
            if signal_type == 'BUY':
                current_price = signal_price * random.uniform(0.85, 0.99)  # 1-15% Verlust
            else:  # SELL
                current_price = signal_price * random.uniform(1.01, 1.15)  # 1-15% Verlust
        
        current_price = round(current_price, 4)
        
        # Performance berechnen
        if signal_type == 'BUY':
            performance = ((current_price - signal_price) / signal_price) * 100
        else:  # SELL
            performance = ((signal_price - current_price) / signal_price) * 100
        
        # Confidence (60-95%)
        confidence = random.randint(60, 95)
        
        # Strategie
        strategy = random.choice(['conservative_trend', 'moderate_momentum', 'aggressive_breakout'])
        
        demo_signals.append({
            'Timestamp': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Coin': coin,
            'Strategy_Signal': signal_type,
            'Signal_Price': signal_price,
            'Current_Price': current_price,
            'Performance_Percent': round(performance, 2),
            'Confidence': confidence,
            'Strategy': strategy,
            'Signal_Timestamp': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Analysis_Result': f"{signal_type} signal for {coin}",
            'Success': 'Yes' if performance > 0 else 'No'
        })
    
    return demo_signals

def save_demo_data():
    """Speichert Demo-Daten als JSON und CSV"""
    demo_data = create_realistic_demo_data()
    
    # Als JSON speichern
    with open('demo_trading_signals.json', 'w', encoding='utf-8') as f:
        json.dump(demo_data, f, indent=2, ensure_ascii=False)
    
    # Als CSV speichern
    df = pd.DataFrame(demo_data)
    df.to_csv('demo_trading_signals.csv', index=False, encoding='utf-8')
    
    # Statistiken ausgeben
    df['Performance_Percent'] = pd.to_numeric(df['Performance_Percent'])
    successful_signals = len(df[df['Performance_Percent'] > 0])
    total_signals = len(df)
    success_rate = (successful_signals / total_signals) * 100
    avg_performance = df['Performance_Percent'].mean()
    
    print(f"✅ {total_signals} Demo-Signale erstellt")
    print(f"📈 Erfolgsrate: {success_rate:.1f}% ({successful_signals}/{total_signals})")
    print(f"📊 Durchschnittliche Performance: {avg_performance:.2f}%")
    print(f"💾 Gespeichert als: demo_trading_signals.json und demo_trading_signals.csv")
    
    return demo_data

if __name__ == "__main__":
    print("Erstelle realistische Demo-Daten für Performance-Testing...")
    save_demo_data()
