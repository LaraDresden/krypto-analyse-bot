#!/usr/bin/env python3
"""
Demo-Daten für Performance-Tracking Test
"""

import pandas as pd
import json
from datetime import datetime, timedelta
import random

def create_demo_data():
    """Erstellt Demo-Daten für Performance-Tracking Tests"""
    
    # Simuliere historische Trading-Signale
    demo_data = []
    coins = ['Bitcoin', 'Ethereum', 'Solana', 'Cardano', 'BNB']
    signals = ['BUY', 'SELL']
    
    base_date = datetime.now() - timedelta(days=60)
    
    for i in range(50):  # 50 Demo Trading-Signale
        signal_date = base_date + timedelta(days=random.randint(0, 55))
        coin = random.choice(coins)
        signal = random.choice(signals)
        signal_price = random.uniform(0.5, 100000)  # Random price
        
        # Simuliere aktuellen Preis basierend auf Signal
        if signal == 'BUY':
            # BUY Signale haben 60% Chance auf Gewinn
            if random.random() < 0.6:
                current_price = signal_price * random.uniform(1.01, 1.25)  # 1-25% Gewinn
            else:
                current_price = signal_price * random.uniform(0.85, 0.99)  # 1-15% Verlust
        else:  # SELL
            # SELL Signale haben 55% Chance auf Gewinn
            if random.random() < 0.55:
                current_price = signal_price * random.uniform(0.85, 0.99)  # Preis fällt = Gewinn für SELL
            else:
                current_price = signal_price * random.uniform(1.01, 1.15)  # Preis steigt = Verlust für SELL
        
        demo_data.append({
            'Zeitstempel': signal_date.strftime("%Y-%m-%d %H:%M:%S"),
            'Coin_Name': coin,
            'Preis_EUR': f"{current_price:.4f}",
            'RSI': random.uniform(20, 80),
            'MACD_Line': random.uniform(-0.01, 0.01),
            'MACD_Signal': random.uniform(-0.01, 0.01),
            'MACD_Histogram': random.uniform(-0.005, 0.005),
            'BB_Position_%': random.uniform(0, 100),
            'MA20': signal_price * random.uniform(0.95, 1.05),
            'MA50': signal_price * random.uniform(0.90, 1.10),
            'MA200': signal_price * random.uniform(0.85, 1.15),
            'MA_Trend': random.choice(['Bullish', 'Bearish', 'Neutral']),
            'Volume_Ratio': random.uniform(0.5, 3.0),
            'Stoch_K': random.uniform(0, 100),
            'ATR': random.uniform(0.01, 0.1),
            'ATR_Percentage': random.uniform(1, 10),
            'Volatility_Level': random.choice(['Low', 'Medium', 'High']),
            'Volatility_Trend': random.choice(['Increasing', 'Decreasing', 'Stable']),
            'Stop_Loss_Long': signal_price * 0.95,
            'News_Sentiment': random.randint(-2, 2),
            'News_Kategorie': random.choice(['Positive', 'Negative', 'Neutral', 'Keine News']),
            'News_Zusammenfassung': 'Demo News',
            'News_Kritisch': random.choice(['Ja', 'Nein']),
            'Status': 'Erfolgreich',
            'Fehler_Details': '',
            'Bestand': random.uniform(0, 1000),
            'Wert_EUR': random.uniform(0, 10000),
            'Strategy_Signal': signal,
            'Confidence_Score': random.uniform(0.3, 0.9),
            'Strategy_Reasoning': f'Demo {signal} Signal für {coin}',
            'Strategy_Name': 'demo_strategy',
            'Signal_Price': f"{signal_price:.4f}",
            'Signal_Timestamp': signal_date.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return demo_data

if __name__ == "__main__":
    demo_data = create_demo_data()
    df = pd.DataFrame(demo_data)
    
    # Speichere als JSON für easy loading
    with open('demo_trading_data.json', 'w', encoding='utf-8') as f:
        json.dump(demo_data, f, indent=2, ensure_ascii=False)
    
    # Speichere auch als CSV
    df.to_csv('demo_trading_data.csv', index=False, encoding='utf-8')
    
    print(f"✅ {len(demo_data)} Demo Trading-Signale erstellt")
    print("📄 Dateien erstellt: demo_trading_data.json, demo_trading_data.csv")
    
    # Zeige Preview
    buy_signals = len([d for d in demo_data if d['Strategy_Signal'] == 'BUY'])
    sell_signals = len([d for d in demo_data if d['Strategy_Signal'] == 'SELL'])
    print(f"📊 {buy_signals} BUY Signale, {sell_signals} SELL Signale")
