import requests
import os
import pandas as pd
import talib
import re

def sende_telegram_nachricht(nachricht):
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Fehler: Telegram-Zugangsdaten nicht in GitHub Secrets gefunden!")
        return

    def escape_markdown(text):
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': nachricht,
            'parse_mode': 'MarkdownV2'
        }
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except Exception as e:
        print(f"Fehler beim Senden der Telegram-Nachricht: {e.response.text}")

def analysiere_bitcoin_alphavantage():
    """
    Holt und analysiert Bitcoin-Daten und sendet bei Erfolg eine Telegram-Nachricht.
    """
    print("Starte Datenabruf von Alpha Vantage...")
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("Fehler: API-Schlüssel nicht in GitHub Secrets gefunden!")
        return

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

        if 'Time Series (Digital Currency Daily)' not in daten:
            print("Fehler: 'Time Series (Digital Currency Daily)' nicht in der API-Antwort gefunden.")
            return

        print("Historische Daten erfolgreich abgerufen!")

        time_series = daten['Time Series (Digital Currency Daily)']
        df = pd.DataFrame.from_dict(time_series, orient='index')
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.rename(columns={'4. close': 'price'})
        df = df.sort_index(ascending=True)

        df['rsi'] = talib.RSI(df['price'], timeperiod=14)

        aktueller_preis = df['price'].iloc[-1]
        aktueller_rsi = df['rsi'].iloc[-1]

        print("\n--- ANALYSE ERGEBNIS ---")
        print(f"Aktueller Bitcoin Preis: ${aktueller_preis:,.2f}")
        print(f"Aktueller 14-Tage-RSI: {aktueller_rsi:.2f}")

        if aktueller_rsi > 70:
            status_text = "🟢 Überkauft \\(Overbought\\) \\- Vorsicht, mögliche Korrektur\\."
        elif aktueller_rsi < 30:
            status_text = "🔴 Überverkauft \\(Oversold\\) \\- Mögliche Kaufgelegenheit\\."
        else:
            status_text = "🟡 Neutral\\."
        print(f"Markt-Status: {status_text}")
        print("------------------------\n")

        # Nachricht direkt mit korrekten Werten erstellen
        telegram_nachricht = (
            f"*BTC Analyse-Update* 🤖\n\n"
            f"Preis: *${aktueller_preis:,.2f}*\n"
            f"14\\-Tage\\-RSI: *{aktueller_rsi:.2f}*\n\n"
            f"*{status_text}*"
        )
        sende_telegram_nachricht(telegram_nachricht)

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    analysiere_bitcoin_alphavantage()
