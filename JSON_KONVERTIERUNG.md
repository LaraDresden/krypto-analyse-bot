# 📝 ANLEITUNG: JSON für .env Datei konvertieren

# Für GitHub Secrets: Komplettes JSON mehrzeilig kopieren
# Für .env Datei: JSON zu einer Zeile konvertieren

# METHODE 1: Online JSON Minifier
# - Gehen Sie zu: https://jsonminify.com/
# - JSON einfügen → Minify → Ergebnis kopieren

# METHODE 2: PowerShell (Windows)
# $json = Get-Content "acoustic-shade-461910-k4-259b36eb241c.json" -Raw
# $minified = $json -replace '\s+', ' '
# Write-Output $minified

# METHODE 3: Python
# import json
# with open('acoustic-shade-461910-k4-259b36eb241c.json') as f:
#     data = json.load(f)
# minified = json.dumps(data, separators=(',', ':'))
# print(minified)

# Ergebnis für .env:
# GOOGLE_CREDENTIALS={"type":"service_account","project_id":"acoustic-shade-461910-k4",...}
