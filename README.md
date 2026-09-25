# iTrakHelper

Ein Python-Tool zur Automatisierung wiederkehrender Aufgaben im **iTrak** Controller
(Metafour NetCourier) — dem internen Buchungs- und Verwaltungstool des Mailrooms.

Das Tool loggt sich per `requests` in iTrak ein und liest Daten direkt über die
JSON-Endpunkte aus, ohne Browser.

## Features

- **Carrier-Zählung (`-cc`)** — zählt für den heutigen Tag die Anzahl der *Pieces*
  pro Carrier und gibt eine Übersicht mit Gesamtsumme aus.

> Weitere Features (z.B. Booking-Automatisierung mit Outlook-Anbindung) sind in
> Arbeit und leben in eigenen Feature-Branches.

## Voraussetzungen

- Python 3.10 oder neuer
- Zugang zu einer iTrak-Instanz (Zugangsdaten)

## Installation

```bash
# Repository klonen
git clone https://github.com/desa-94/iTrakHelper.git
cd iTrakHelper

# Virtuelle Umgebung anlegen und aktivieren (Windows)
python -m venv venv
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Konfiguration

Die Zugangsdaten werden über eine `.env`-Datei geladen (wird von git ignoriert).

1. Kopiere die Vorlage:
   ```bash
   copy .env.example .env
   ```
2. Trage in `.env` deine echten Werte ein:
   ```
   iTrak_CONTROLLER_URL=https://<dein-itrak-host>/online/inbound/controller
   iTrak_ACCESS_CODE=dein_access_code
   iTrak_USERNAME=dein_username
   iTrak_PASSWORD=[REDACTED_PASSWORD]
   ```

## Verwendung

```bash
# Pieces pro Carrier für heute zählen
py main.py -cc

# Hilfe anzeigen
py main.py -h
```

## Projektstruktur

```
iTrakHelper/
├── main.py            # CLI-Einstiegspunkt, Login und Kommandos
├── filter_helper.py   # Parsen der Controller-Filter und Bauen des Payloads
├── requirements.txt   # Python-Abhängigkeiten
├── .env.example       # Vorlage für die Konfiguration
└── .gitignore
```

## Sicherheit

- Die `.env` mit deinen echten Zugangsdaten wird **nie** committet (steht in `.gitignore`).
- Teile deine `.env` nicht und lade sie nicht hoch — nur die `.env.example` gehört ins Repo.
