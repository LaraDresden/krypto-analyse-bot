#!/usr/bin/env python3
"""
Demo Data Generator für Crypto Analysis Dashboard
Erstellt realistische CSV-Daten im Google Sheets Format
"""

import csv
import random
import datetime
from decimal import Decimal

def generate_demo_data():
    """Generiert realistische Krypto-Analysedaten"""
    
    # Liste der Kryptowährungen mit realistischen Werten
    crypto_data = [
        {"name": "Bitcoin", "symbol": "BTC", "base_price": 43500, "volatility": 0.03},
        {"name": "Ethereum", "symbol": "ETH", "base_price": 2850, "volatility": 0.04},
        {"name": "Binance Coin", "symbol": "BNB", "base_price": 295, "volatility": 0.05},
        {"name": "Cardano", "symbol": "ADA", "base_price": 0.48, "volatility": 0.06},
        {"name": "Solana", "symbol": "SOL", "base_price": 92, "volatility": 0.07},
        {"name": "Polkadot", "symbol": "DOT", "base_price": 7.2, "volatility": 0.06},
        {"name": "Chainlink", "symbol": "LINK", "base_price": 14.8, "volatility": 0.05},
        {"name": "Polygon", "symbol": "MATIC", "base_price": 0.75, "volatility": 0.08},
        {"name": "Dogecoin", "symbol": "DOGE", "base_price": 0.085, "volatility": 0.12},
        {"name": "XRP", "symbol": "XRP", "base_price": 0.52, "volatility": 0.08}
    ]
    
    # CSV Header - exakt wie Backend es erstellt
    fieldnames = [
        'timestamp', 'coin', 'current_price', 'price_change_24h', 'price_change_7d',
        'volume_24h', 'market_cap', 'fear_greed_index', 'rsi', 'macd_signal',
        'bb_position', 'support_level', 'resistance_level', 'atr', 'stoch_k',
        'stoch_d', 'williams_r', 'news_sentiment', 'ai_recommendation',
        'strategy_signal', 'confidence_score', 'stop_loss', 'take_profit',
        'portfolio_weight', 'portfolio_value'
    ]
    
    # Demo-Daten generieren
    rows = []
    current_time = datetime.datetime.now()
    
    for i, crypto in enumerate(crypto_data):
        # Zufällige aber realistische Werte generieren
        price_change_24h = random.uniform(-8, 12)  # Prozent
        price_change_7d = random.uniform(-15, 25)   # Prozent
        
        current_price = crypto["base_price"] * (1 + random.uniform(-0.02, 0.02))
        volume_24h = random.uniform(500000000, 15000000000)  # Volumen
        market_cap = current_price * random.uniform(18000000, 950000000)  # Market Cap
        
        # Technische Indikatoren
        rsi = random.uniform(25, 75)
        macd_signal = random.choice(['BUY', 'SELL', 'HOLD'])
        bb_position = random.uniform(0.2, 0.8)  # Bollinger Band Position
        
        # Support/Resistance
        support_level = current_price * random.uniform(0.92, 0.98)
        resistance_level = current_price * random.uniform(1.02, 1.08)
        
        # ATR und Stochastic
        atr = current_price * random.uniform(0.02, 0.06)
        stoch_k = random.uniform(20, 80)
        stoch_d = stoch_k + random.uniform(-5, 5)
        williams_r = random.uniform(-80, -20)
        
        # Sentiment und AI - spezielle Behandlung für Dogecoin
        if crypto["name"] == "Dogecoin":
            # Dogecoin hat oft extremere Sentiment-Schwankungen
            news_sentiment = random.choice(['Very Bullish', 'Bullish', 'Bearish', 'Very Bearish', 'Neutral'])
            ai_recommendation = random.choice(['Strong Buy', 'Buy', 'Hold', 'Sell', 'Speculative Buy'])
            # Höhere Volatilität in Confidence Score für Meme Coins
            confidence_score = random.uniform(0.4, 0.85)
        else:
            news_sentiment = random.choice(['Bullish', 'Bearish', 'Neutral'])
            ai_recommendation = random.choice(['Strong Buy', 'Buy', 'Hold', 'Sell'])
            confidence_score = random.uniform(0.6, 0.95)
        
        strategy_signal = random.choice(['BUY', 'SELL', 'HOLD'])
        
        # Stop Loss / Take Profit
        stop_loss = current_price * random.uniform(0.90, 0.95)
        take_profit = current_price * random.uniform(1.05, 1.15)
        
        # Portfolio Daten
        portfolio_weight = random.uniform(5, 25)  # Prozent
        portfolio_value = random.uniform(1000, 50000)  # Euro
        
        # Timestamp (verschiedene Zeiten für Realismus)
        timestamp = (current_time - datetime.timedelta(minutes=i*5)).isoformat()
        
        row = {
            'timestamp': timestamp,
            'coin': crypto["name"],
            'current_price': f"{current_price:.4f}",
            'price_change_24h': f"{price_change_24h:.2f}",
            'price_change_7d': f"{price_change_7d:.2f}",
            'volume_24h': f"{volume_24h:.0f}",
            'market_cap': f"{market_cap:.0f}",
            'fear_greed_index': random.randint(15, 85),
            'rsi': f"{rsi:.2f}",
            'macd_signal': macd_signal,
            'bb_position': f"{bb_position:.3f}",
            'support_level': f"{support_level:.4f}",
            'resistance_level': f"{resistance_level:.4f}",
            'atr': f"{atr:.4f}",
            'stoch_k': f"{stoch_k:.2f}",
            'stoch_d': f"{stoch_d:.2f}",
            'williams_r': f"{williams_r:.2f}",
            'news_sentiment': news_sentiment,
            'ai_recommendation': ai_recommendation,
            'strategy_signal': strategy_signal,
            'confidence_score': f"{confidence_score:.3f}",
            'stop_loss': f"{stop_loss:.4f}",
            'take_profit': f"{take_profit:.4f}",
            'portfolio_weight': f"{portfolio_weight:.2f}",
            'portfolio_value': f"{portfolio_value:.2f}"
        }
        
        rows.append(row)
    
    return fieldnames, rows

def create_demo_csv(filename="demo_crypto_data.csv"):
    """Erstellt eine CSV-Datei mit Demo-Daten"""
    fieldnames, rows = generate_demo_data()
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Demo CSV erstellt: {filename}")
    print(f"📊 {len(rows)} Datensätze generiert")
    print(f"🏷️  {len(fieldnames)} Spalten: {', '.join(fieldnames[:5])}...")
    
    return filename

if __name__ == "__main__":
    create_demo_csv()
