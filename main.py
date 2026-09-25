import argparse
import os
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup as bs
from dotenv import load_dotenv
from filter_helper import FilterHelper

# === iTrak Funktionen ===


def login(
    session: requests.Session,
    controller_url: str,
    access_code: str,
    username: str,
    password: str,
) -> tuple[str, str]:
    """Loggt ein und gibt (CSRF-Token, Controller-HTML) zurück.

    Startet bei der iTrak Controller-Seite, folgt dem Redirect zur Login-Seite,
    schickt die Zugangsdaten und landet nach erfolgreichem Login wieder auf der
    Controller-Seite.
    """
    response = session.get(controller_url)

    soup = bs(response.text, "html.parser")
    csrf_input = soup.find("input", {"name": "_csrf"})
    form = soup.find("form", {"id": "mainform"})
    if csrf_input is None or form is None:
        raise RuntimeError("Login-Formular nicht gefunden. Stimmt die CONTROLLER_URL?")

    auth_url = urljoin(response.url, form["action"])
    payload = {
        "_csrf": csrf_input["value"],
        "accessCode": access_code,
        "username": username,
        "password": password,
    }

    result = session.post(auth_url, data=payload, headers={"Referer": response.url})

    soup2 = bs(result.text, "html.parser")
    csrf_meta = soup2.find("meta", {"name": "_csrf"})
    if csrf_meta is None:
        raise RuntimeError(
            "Login fehlgeschlagen. Bitte Zugangsdaten in der .env prüfen."
        )

    return csrf_meta["content"], result.text


def fetch_jobs(
    session: requests.Session,
    controller_url: str,
    csrf: str,
    fh: FilterHelper,
    carrier_id: str = "",
) -> dict:
    """Holt die Jobs von heute für einen Carrier vom /listdata Endpoint."""
    today_str = datetime.now().strftime("%a, %d-%b-%Y")

    fh.set_filter("filterdateperiod", "today")
    fh.set_filter("fromDate", today_str)
    fh.set_filter("toDate", today_str)
    fh.set_filter("carrierCompanyId", carrier_id)

    headers = {
        "X-CSRF-TOKEN": csrf,
        "X-Requested-With": "XMLHttpRequest",
    }

    listdata_url = controller_url + "/listdata"
    response = session.post(listdata_url, data=fh.build_payload(), headers=headers)

    if response.status_code == 200:
        return response.json()

    print(
        f"  FEHLER bei Carrier {carrier_id}: "
        f"{response.status_code} - {response.text[:200]}"
    )
    return {}


# === Kommandos ===


# Anzeige-Reihenfolge der Gruppen (wie auf dem Zettel im Mailroom)
CARRIER_GROUP_ORDER = [
    "Amazon",
    "UPS",
    "DHL",
    "DHL Express",
    "GLS",
    "FedEx",
    "DPD",
    "Hermes",
    "Deutsche Post",
    "Sonstiges",
]


def classify_carrier(label: str) -> str:
    """Ordnet einen Carrier-Namen einer der festen Gruppen auf dem Zettel zu.

    Alles was zu keiner Gruppe passt (z.B. Courier (Other)),
    landet in 'Sonstiges'.
    """
    name = label.lower()
    if "amazon" in name:
        return "Amazon"
    if "dhl express" in name:  # muss VOR "dhl" geprüft werden!
        return "DHL Express"
    if "dhl" in name:
        return "DHL"
    if "ups" in name:
        return "UPS"
    if "gls" in name:
        return "GLS"
    if "fedex" in name:
        return "FedEx"
    if "dpd" in name:
        return "DPD"
    if "hermes" in name:
        return "Hermes"
    if "deutsche post" in name:
        return "Deutsche Post"
    return "Sonstiges"


def cmd_count_carrier(
    session: requests.Session, controller_url: str, csrf: str, fh: FilterHelper
) -> None:
    """Zählt die Pieces pro Carrier für heute."""
    carriers = fh.get_options("carrierCompanyId")

    # Pieces je Gruppe sammeln (alle Gruppen starten bei 0)
    group_pieces = {group: 0 for group in CARRIER_GROUP_ORDER}

    for carrier in carriers:
        data = fetch_jobs(session, controller_url, csrf, fh, carrier["value"])

        jobs = data.get("jobs", [])
        carrier_pieces = 0
        for job in jobs:
            try:
                carrier_pieces += int(job.get("pieces", 0))
            except (ValueError, TypeError):
                pass

        group = classify_carrier(carrier["label"])
        group_pieces[group] += carrier_pieces

    # Ausgabe in fester Reihenfolge (wie auf dem Zettel)
    width = 30
    print("=" * width)
    print("Pieces pro Carrier (heute)")
    print("=" * width)
    for group in CARRIER_GROUP_ORDER:
        count = str(group_pieces[group])
        # Führungspunkte zwischen Name und Zahl für leichtes Ablesen
        dots = "." * (width - len(group) - len(count) - 1)
        print(f"{group} {dots} {count}")
    print("-" * width)
    total = str(sum(group_pieces.values()))
    dots = "." * (width - len("GESAMT") - len(total) - 1)
    print(f"GESAMT {dots} {total}")
    print("=" * width)


# === CLI ===


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="iTrakHelper — Automatisierung für iTrak Controller"
    )
    parser.add_argument(
        "-cc",
        "--count_carrier",
        action="store_true",
        help="Zählt die Pieces pro Carrier für heute",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not any(vars(args).values()):
        print("Kein Kommando angegeben. Nutze -h für Hilfe.")
        return

    load_dotenv()
    controller_url = os.getenv("iTrak_CONTROLLER_URL")
    access_code = os.getenv("iTrak_ACCESS_CODE")
    username = os.getenv("iTrak_USERNAME")
    password = os.getenv("iTrak_PASSWORD")

    if not all([controller_url, access_code, username, password]):
        print("Konfiguration unvollständig. Bitte .env anlegen (siehe .env.example).")
        return

    session = requests.Session()
    csrf, controller_html = login(
        session, controller_url, access_code, username, password
    )
    fh = FilterHelper(controller_html)
    print("Login erfolgreich!\n")

    if args.count_carrier:
        cmd_count_carrier(session, controller_url, csrf, fh)


if __name__ == "__main__":
    main()
