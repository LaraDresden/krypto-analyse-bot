import requests
import os # Wird benötigt, um auf Secrets zuzugreifen
import pandas as pd
import talib

def analysiere_bitcoin_alphavantage():
    """
    Holt historische Bitcoin-Daten von Alpha Vantage, berechnet den RSI 
    und gibt das Ergebnis aus.
    """
    print("Starte Datenabruf von Alpha Vantage...")

    # Der API-Schlüssel wird sicher aus den GitHub Secrets geladen
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')

    if not api_key:
        print("Fehler: API-Schlüssel nicht gefunden!")
        return

    # URL und Parameter für Alpha Vantage
    url = 'https://www.alphavantage.co/query'
    params = {
        'function': 'DIGITAL_CURRENCY_DAILY',
        'symbol': 'BTC',
        'market': 'USD',
        'apikey': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        daten = response.json()
        
        # Fehlerprüfung für die API-Antwort
        if 'Error Message' in daten:
            print(f"Fehler von Alpha Vantage API: {daten['Error Message']}")
            return

        print("Historische Daten erfolgreich abgerufen!")

        # --- Datenaufbereitung mit Pandas ---
        time_series = daten['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        
        # Spalten umbenennen und nur den Schlusskurs behalten
        df = df.rename(columns={'4a. close (USD)': 'price'})
        df = df.sort_index(ascending=True) # Sortieren, älteste zuerst

        # --- Technische Analyse mit TA-Lib ---
        df['rsi'] = talib.RSI(df['price'], timeperiod=14)

        # --- Ergebnisse ausgeben ---
        aktueller_preis = df['price'].iloc[-1]
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
    analysiere_bitcoin_alphavantage()
