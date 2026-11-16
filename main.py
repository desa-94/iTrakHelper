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
    collection_location_ids: list | None = None,
) -> dict:
    """Holt die Jobs von heute für einen Carrier vom /listdata Endpoint."""
    today_str = datetime.now().strftime("%a, %d-%b-%Y")

    fh.set_filter("filterdateperiod", "today")
    fh.set_filter("fromDate", today_str)
    fh.set_filter("toDate", today_str)
    fh.set_filter("carrierCompanyId", carrier_id)
    # Optional nur bestimmte Collection-Locations abfragen
    # (z.B. um Einschreiben ein- oder auszuschließen).
    if collection_location_ids is not None:
        fh.set_filter("collectionLocationId", collection_location_ids)

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


# Standort, dessen Mengen gezählt werden sollen (Label-Teilstring, klein).
# Nur dieser Standort fließt in die Zählung ein — andere (Berlin, MUC14,
# Amazon DE, ...) werden bewusst ignoriert.
LOCATION_FILTER = "muc21"


def split_locations(fh: FilterHelper) -> tuple[list, list]:
    """Teilt die relevanten Collection-Locations in (normal, einschreiben) auf.

    Es werden NUR Standorte berücksichtigt, deren Label LOCATION_FILTER enthält
    (also MUC21). Davon gilt alles mit 'Einschreiben' im Label als Einschreiben,
    der Rest (das normale MUC21) als Pakete. Alle anderen Standorte werden
    ignoriert, damit keine fremden Mengen mitgezählt werden.
    """
    normal_ids = []
    einschreiben_ids = []
    for loc in fh.get_options("collectionLocationId"):
        label = loc["label"].lower()
        if LOCATION_FILTER not in label:
            continue  # fremder Standort -> ignorieren
        if "einschreiben" in label:
            einschreiben_ids.append(loc["value"])
        else:
            normal_ids.append(loc["value"])
    return normal_ids, einschreiben_ids


def count_pieces(data: dict) -> int:
    """Summiert das Feld 'pieces' über alle Jobs einer /listdata-Antwort."""
    total = 0
    for job in data.get("jobs", []):
        try:
            total += int(job.get("pieces", 0))
        except (ValueError, TypeError):
            pass
    return total


def cmd_count_carrier(
    session: requests.Session, controller_url: str, csrf: str, fh: FilterHelper
) -> None:
    """Zählt die Pieces pro Carrier für heute."""
    carriers = fh.get_options("carrierCompanyId")
    normal_ids, einschreiben_ids = split_locations(fh)

    # Pieces je Gruppe sammeln (alle Gruppen starten bei 0)
    group_pieces = {group: 0 for group in CARRIER_GROUP_ORDER}

    # Carrier-Zählung NUR auf den normalen Locations — Einschreiben fließen
    # hier NICHT ein (werden separat ausgewiesen).
    for carrier in carriers:
        data = fetch_jobs(
            session, controller_url, csrf, fh, carrier["value"], normal_ids
        )
        carrier_pieces = count_pieces(data)
        group = classify_carrier(carrier["label"])
        group_pieces[group] += carrier_pieces

    # Einschreiben separat zählen (eigene Location, NICHT zur Paketsumme addiert).
    einschreiben_pieces = 0
    if einschreiben_ids:
        data = fetch_jobs(session, controller_url, csrf, fh, "", einschreiben_ids)
        einschreiben_pieces = count_pieces(data)

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
    # Einschreiben als separate Info — bewusst NICHT in der Paketsumme.
    es = str(einschreiben_pieces)
    dots = "." * (width - len("Einschreiben") - len(es) - 1)
    print(f"Einschreiben {dots} {es}")
    print("=" * width)



def cmd_debug_jobs(
    session: requests.Session, controller_url: str, csrf: str, fh: FilterHelper
) -> None:
    """Diagnose: zeigt genau, welche Jobs gezaehlt werden.

    Dumpt das erste Job-Objekt roh (um die echten Feldnamen zu sehen) und
    bricht die Pieces pro Collection-Location herunter, damit sichtbar wird,
    ob fremde Standorte (z.B. Berlin/MUC14) mitgezaehlt werden.
    """
    import json

    normal_ids, einschreiben_ids = split_locations(fh)
    all_locs = fh.get_options("collectionLocationId")
    print("=== Collection-Locations im Dropdown ===")
    for loc in all_locs:
        print(f"  {loc['value']:<12} {loc['label']}")
    print()
    print("Als NORMAL eingestuft:", normal_ids)
    print("Als EINSCHREIBEN eingestuft:", einschreiben_ids)
    print()

    # Ein Request ueber ALLE Carrier auf den 'normalen' Locations
    data = fetch_jobs(session, controller_url, csrf, fh, "", normal_ids)
    jobs = data.get("jobs", [])
    print(f"Top-Level-Keys der Antwort: {list(data.keys())}")
    print(f"Jobs zurueckgegeben: {len(jobs)}")
    print()

    if jobs:
        print("=== Erstes Job-Objekt (roh) ===")
        print(json.dumps(jobs[0], indent=2, ensure_ascii=False, default=str))
        print()

    per_location = {}
    total = 0
    print("=== Job-Uebersicht ===")
    for job in jobs:
        jobno = job.get("internalJobNumber", "?")
        carrier = job.get("carrierCompany", "?")
        loc = job.get("collectFrom", job.get("collectionLocation", "?"))
        pieces = job.get("pieces", 0)
        try:
            p = int(pieces)
        except (ValueError, TypeError):
            p = 0
        total += p
        per_location[str(loc)] = per_location.get(str(loc), 0) + p
        print(f"  {str(jobno):<12} {str(carrier):<18} "
              f"loc={str(loc):<28} pieces={pieces}")

    print()
    print("=== Pieces pro Collection-Location (so wie im Job-Feld) ===")
    for loc, pcs in sorted(per_location.items()):
        print(f"  {loc:<35} {pcs}")
    print(f"\nGESAMT pieces (normale Locations, alle Carrier): {total}")


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
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Diagnose-Ausgabe: zeigt welche Jobs/Locations gezählt werden",
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

    if args.debug:
        cmd_debug_jobs(session, controller_url, csrf, fh)
    elif args.count_carrier:
        cmd_count_carrier(session, controller_url, csrf, fh)


if __name__ == "__main__":
    main()
