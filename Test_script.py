
import requests
import os
import pandas as pd
# talib wird für diesen Test nicht benötigt

def debug_spaltennamen():
    print("Starte Datenabruf von Alpha Vantage für Debugging...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("Fehler: API-Schlüssel nicht in GitHub Secrets gefunden!")
        return

    url = 'https://www.alphavantage.co/query'
    params = { 'function': 'DIGITAL_CURRENCY_DAILY', 'symbol': 'BTC', 'market': 'USD', 'apikey': api_key }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        daten = response.json()
        print("Daten erfolgreich abgerufen!")

        # Überprüfen, ob der erwartete Schlüssel vorhanden ist
        if 'Time Series (Digital Currency Daily)' not in daten:
            print("Fehler: 'Time Series (Digital Currency Daily)' nicht in der API-Antwort gefunden. Antwort:")
            print(daten)
            return

        time_series = daten['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')

        # --- DEBUGGING-SCHRITT ---
        # Dieser Befehl gibt uns die exakten Namen aller verfügbaren Spalten aus.
        print("\n--- Verfügbare Spalten ---")
        print(df.columns)
        print("--------------------------\n")

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    debug_spaltennamen()
