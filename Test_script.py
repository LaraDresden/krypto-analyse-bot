import ccxt # Importiert die neue ccxt-Bibliothek
import pandas as pd
import talib

def analysiere_bitcoin_binance():
    """
    Holt historische Bitcoin-Daten direkt von der Binance API, 
    berechnet den RSI und gibt das Ergebnis aus.
    """
    print("Starte Datenabruf von Binance...")

    try:
        # Initialisiert den Binance-Connector
        binance = ccxt.binance()

        # Holte die letzten 40 täglichen Kerzen (OHLCV) für BTC/USDT
        # Wir holen etwas mehr als 30, um sicherzustellen, dass der RSI-Wert korrekt berechnet wird
        ohlcv = binance.fetch_ohlcv('BTC/USDT', '1d', limit=40)

        print("Historische Daten erfolgreich abgerufen!")

        # --- Datenaufbereitung mit Pandas ---
        # Die Daten von ccxt sind bereits gut strukturiert
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # --- Technische Analyse mit TA-Lib ---
        df['rsi'] = talib.RSI(df['close'], timeperiod=14)

        # --- Ergebnisse ausgeben ---
        aktueller_preis = df['close'].iloc[-1]
        aktueller_rsi = df['rsi'].iloc[-1]

        print("\n--- ANALYSE ERGEBNIS ---")
        print(f"Aktueller Bitcoin Preis: ${aktueller_preis:,.2f}")
        print(f"Aktueller 14-Tage-RSI: {aktueller_rsi:.2f}")

        if aktueller_rsi > 70:
            print("Markt-Status: 🟢 Überkauft (Overbought) - Vorsicht, mögliche Korrektur.")
        elif aktueller_rsi < 30:
            print("Markt-Status: 🔴 Überverkauft (Oversold) - Mögliche Kaufgelegenheit.")
        else:
            print("Markt-Status: 🟡 Neutral.")
        print("------------------------\n")

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    analysiere_bitcoin_binance()