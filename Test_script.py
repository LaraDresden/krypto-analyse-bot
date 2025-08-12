import requests
import os
import pandas as pd
import talib
import re # Importiert die Bibliothek für Text-Ersetzung

def sende_telegram_nachricht(nachricht):
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Fehler: Telegram-Zugangsdaten nicht in GitHub Secrets gefunden!")
        return

    # --- KORREKTUR: Bereinigt die Nachricht für MarkdownV2 ---
    def escape_markdown(text):
        # Maskiert problematische Zeichen für Telegrams MarkdownV2
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    # Nachricht mit bereinigten Werten erstellen
    try:
        # Die Werte aus der Nachricht extrahieren und bereinigen
        preis_str = re.search(r"Preis: \*(.*?)\*", nachricht).group(1)
        rsi_str = re.search(r"14-Tage-RSI: \*(.*?)\*", nachricht).group(1)
        status_str = re.search(r"\n\n\*(.*?)\*", nachricht).group(1)

        # Die bereinigte Nachricht zusammenbauen
        bereinigte_nachricht = (
            f"*BTC Analyse-Update* 🤖\n\n"
            f"Preis: *{escape_markdown(preis_str)}*\n"
            f"14-Tage-RSI: *{escape_markdown(rsi_str)}*\n\n"
            f"*{escape_markdown(status_text)}*"
        )
    except AttributeError:
         # Fallback, falls die Extraktion fehlschlägt
        bereinigte_nachricht = nachricht

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': bereinigte_nachricht,
        'parse_mode': 'MarkdownV2' # Wir verwenden die neuere Version
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except Exception as e:
        # Gibt eine detailliertere Fehlermeldung aus
        print(f"Fehler beim Senden der Telegram-Nachricht: {e} - Antwort: {e.response.text}")

# Der Rest des Skripts bleibt unverändert
def analysiere_bitcoin_alphavantage():
    print("Starte Datenabruf von Alpha Vantage...")
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
            status_text = "🟢 Überkauft (Overbought) - Vorsicht, mögliche Korrektur."
        elif aktueller_rsi < 30:
            status_text = "🔴 Überverkauft (Oversold) - Mögliche Kaufgelegenheit."
        else:
            status_text = "🟡 Neutral."
        print(f"Markt-Status: {status_text}")
        print("------------------------\n")

        telegram_nachricht = (
            f"*BTC Analyse-Update* 🤖\n\n"
            f"Preis: *${aktueller_preis:,.2f}*\n"
            f"14-Tage-RSI: *{aktueller_rsi:.2f}*\n\n"
            f"*{status_text}*"
        )
        sende_telegram_nachricht(telegram_nachricht)

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    analysiere_bitcoin_alphavantage()
