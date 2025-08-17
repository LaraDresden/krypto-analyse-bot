import gspread
import json
import os
from datetime import datetime

def test_google_sheet_connection():
    """Ein isolierter Test, um die Google Sheets Verbindung zu überprüfen."""
    print("Starte Google Sheets Verbindungstest...")
    try:
        credentials_json_str = os.getenv('GOOGLE_CREDENTIALS')
        if not credentials_json_str:
            print("Fehler: GOOGLE_CREDENTIALS Secret nicht gefunden!")
            return

        credentials_dict = json.loads(credentials_json_str)
        
        gc = gspread.service_account_from_dict(credentials_dict)
        
        print("Authentifizierung erfolgreich. Versuche, Spreadsheet zu öffnen...")
        spreadsheet = gc.open("Krypto-Analyse-DB")
        worksheet = spreadsheet.worksheet("Market_Data")
        print("Spreadsheet und Tabellenblatt erfolgreich gefunden.")
        
        test_zeile = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Verbindungstest", "123.45", "50.00", "Erfolgreich", "Test erfolgreich"]
        
        worksheet.append_row(test_zeile)
        print(">>> ERFOLG! Testzeile wurde erfolgreich in Google Sheet geschrieben.")

    except gspread.exceptions.APIError as e:
        print(f">>> API FEHLER! Google hat die Anfrage abgelehnt. Grund:")
        print(e.response.text)
    except Exception as e:
        print(f">>> ALLGEMEINER FEHLER! Ein unerwarteter Fehler ist aufgetreten:")
        print(e)

if __name__ == "__main__":
    test_google_sheet_connection()
