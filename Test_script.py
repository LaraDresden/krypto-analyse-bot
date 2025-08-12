import requests
import os
import pandas as pd
import talib
import re # Wichtig für die Text-Ersetzung

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
        'parse_mode': 'MarkdownV2'
    }
    try:
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
    # ... (Der gesamte Datenabruf-Teil bleibt gleich) ...
    try:
        # ... (API-Aufruf und Datenverarbeitung wie zuvor) ...
        # Ab hier ist der Code angepasst:
        
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        # ... (Rest des try-Blocks bis zur Ausgabe) ...
        # ...

        # --- FINALE KORREKTUR: Systematisches Escaping für Telegram ---

        def escape_markdown(text):
            """Maskiert alle Sonderzeichen für Telegrams MarkdownV2."""
            text = str(text)
            escape_chars = r'_*[]()~`>#+-=|{}.!'
            return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

        # 1. Saubere Variablen erstellen
        preis_str = f"${aktueller_preis:,.2f}"
        rsi_str = f"{aktueller_rsi:.2f}"

        if aktueller_rsi > 70:
            status_text = "🟢 Überkauft (Overbought) - Vorsicht, mögliche Korrektur."
        elif aktueller_rsi < 30:
            status_text = "🔴 Überverkauft (Oversold) - Mögliche Kaufgelegenheit."
        else:
            status_text = "🟡 Neutral."
            
        print(f"Markt-Status: {status_text}")
        print("------------------------\n")
        
        # 2. Nachricht mit maskierten Werten zusammenbauen
        telegram_nachricht = (
            f"*BTC Analyse\\-Update* 🤖\n\n"
            f"Preis: *{escape_markdown(preis_str)}*\n"
            f"14\\-Tage\\-RSI: *{escape_markdown(rsi_str)}*\n\n"
            f"*{escape_markdown(status_text)}*"
        )
        sende_telegram_nachricht(telegram_nachricht)

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

# Der folgende Code muss außerhalb der Funktion stehen
if __name__ == "__main__":
    # Dieser Teil muss hier stehen, damit das Skript ausgeführt wird
    import requests
    import os
    import pandas as pd
    import talib
    import re
    analysiere_bitcoin_alphavantage()
