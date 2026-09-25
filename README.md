# iTrakHelper

A Python tool for automating recurring tasks in the **iTrak** controller
(Metafour NetCourier) — the mailroom's internal booking and management tool.

The tool logs into iTrak using `requests` and reads data directly from the
JSON endpoints, without a browser.

## Features

- **Carrier count (`-cc`)** — counts the number of *pieces* per carrier for
  the current day and prints an overview with a total.

> Additional features (e.g. booking automation with Outlook integration) are
> in progress and live in their own feature branches.

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

## Project structure

```
iTrakHelper/
├── main.py            # CLI entry point, login and commands
├── filter_helper.py   # Parses the controller filters and builds the payload
├── requirements.txt   # Python dependencies
├── .env.example       # Configuration template
└── .gitignore
```
