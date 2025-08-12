import requests
import os
import pandas as pd
import talib

def sende_telegram_nachricht(nachricht):
    """Sendet eine formatierte Nachricht an Ihren Telegram-Bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Fehler: Telegram-Zugangsdaten nicht in GitHub Secrets gefunden!")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        'chat_id': chat_id,
        'text': nachricht,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Telegram-Benachrichtigung erfolgreich gesendet!")
    except Exception as e:
        print(f"Fehler beim Senden der Telegram-Nachricht: {e}")

def analysiere_bitcoin_alphavantage():
    # ... (der gesamte Code von hier bis zum print-Block bleibt genau gleich) ...
    print("Starte Datenabruf von Alpha Vantage...")
    # ...
    # --- Ergebnisse ausgeben ---
    aktueller_preis = df['price'].iloc[-1]
    aktueller_rsi = df['rsi'].iloc[-1]

    # Wir erstellen die Terminal-Ausgabe wie bisher
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

    # --- Nachricht für Telegram formatieren und senden ---
    telegram_nachricht = (
        f"*BTC Analyse-Update* 🤖\n\n"
        f"Preis: *${aktueller_preis:,.2f}*\n"
        f"14-Tage-RSI: *{aktueller_rsi:.2f}*\n\n"
        f"*{status_text}*"
    )
    sende_telegram_nachricht(telegram_nachricht)

if __name__ == "__main__":
    analysiere_bitcoin_alphavantage()
