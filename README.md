# iTrakHelper

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

A Python tool for automating recurring tasks in the **iTrak** controller
(Metafour NetCourier) — the mailroom's internal booking and management tool.

The tool logs into iTrak using `requests` and reads data directly from the
JSON endpoints, without a browser. It supports the daily volume reporting that
would otherwise be copied by hand.

## Background — why this exists

Every evening the mailroom fills in a volume report (*Mengenreporting*): how
many parcels and letters arrived that day, broken down by carrier. These
numbers end up on a sheet that gets archived and in a SharePoint file.

The old way had several manual steps:

1. Wait until the colleague from the loading bay arrived in the evening.
2. Receive a hand-written note with their counts.
3. Copy those numbers onto our own sheet (which is archived).
4. Only then type everything into the digital report.

iTrakHelper replaces all of that: the numbers come straight from the system we
book parcels and letters into, so they are **exactly what actually arrived —
no more, no less**. One click, read the numbers off the screen, write them on
the sheet and into the report. The loading bay no longer needs to collect them
by hand, and there is no more waiting for a note to be handed over.

## Features

- **Carrier count (`-cc`)** — counts the number of *pieces* per carrier for the
  current day and prints an overview grouped into fixed carrier buckets
  (Amazon, UPS, DHL, DHL Express, GLS, FedEx, DPD, Hermes, Deutsche Post,
  Sonstiges) with a total.
  - Registered mail (*Einschreiben*) is counted **separately** via its own
    collection location and is **not** added to the package total.

## Requirements

- Python 3.10 or newer
- Access to an iTrak instance (credentials)

## Installation

```bash
# Clone the repository
git clone https://github.com/desa-94/iTrakHelper.git
cd iTrakHelper

# Create and activate a virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Credentials are loaded from a `.env` file (ignored by git).

1. Copy the template:
   ```bash
   copy .env.example .env
   ```
2. Fill in your real values in `.env`:
   ```
   iTrak_CONTROLLER_URL=https://<your-itrak-host>/online/inbound/controller
   iTrak_ACCESS_CODE=your_access_code
   iTrak_USERNAME=your_username
   iTrak_PASSWORD=[REDACTED_PASSWORD]
   ```

## Usage

```bash
# Count pieces per carrier for today
py main.py -cc

# Show help
py main.py -h
```

On Windows you can also double-click `count_carrier.bat`, which activates the
virtual environment and runs `py main.py -cc` for you.

### Example output

```
==============================
Pieces pro Carrier (heute)
==============================
Amazon ..................... 14
UPS ........................ 32
DHL ......................... 6
DHL Express ................ 38
GLS ......................... 1
FedEx ....................... 2
DPD ........................ 14
Hermes ...................... 1
Deutsche Post .............. 30
Sonstiges ................... 2
------------------------------
GESAMT .................... 140
==============================
Einschreiben ............... 12
==============================
```

(Numbers are illustrative.)

## Troubleshooting

- **`Login fehlgeschlagen`** — the credentials in `.env` are wrong or
  incomplete. Double-check `iTrak_ACCESS_CODE`, `iTrak_USERNAME` and
  `iTrak_PASSWORD`.
- **`Konfiguration unvollständig`** — no `.env` file was found, or a value is
  missing. Copy `.env.example` to `.env` and fill in all fields.
- **`ModuleNotFoundError`** — the virtual environment is not active. Run
  `venv\Scripts\activate` first, then `pip install -r requirements.txt`.
- **Wrong or inflated counts** — only the MUC21 location is counted. If your
  site differs, adjust `LOCATION_FILTER` at the top of the commands section in
  `main.py`.

## Project structure

```
iTrakHelper/
├── main.py            # CLI entry point, login and commands
├── filter_helper.py   # Parses the controller filters and builds the payload
├── count_carrier.bat  # Windows one-click launcher for -cc
├── requirements.txt   # Python dependencies
├── .env.example       # Configuration template
└── .gitignore
```
