from bs4 import BeautifulSoup as bs

# HTML-Feld-Name → Payload-Feld-Name
FILTER_FIELD_MAP = {
    # Datum
    "filterdateperiod": "filters.period",
    "fromDate": "filters.fromDate",
    "toDate": "filters.toDate",
    # Text-Felder
    "internalJobNumber": "filters.internalJobNumber",
    "carrierJobNumber": "filters.carrierJobNumber",
    "floor": "filters.floor",
    "department": "filters.department",
    "desk": "filters.desk",
    "secondReference": "filters.secondReference",
    # Single-Selects
    "carrierCompanyId": "filters.carrierCompanyId",
    "serviceId": "filters.serviceId",
    "jobCategoryId": "filters.jobCategoryId",
    # Multi-Selects
    "collectionLocationId": "filters.collectionLocationId[]",
    "deliveryLocationId": "filters.deliveryLocationId",
    # Hidden-Felder (von Typeahead/Autocomplete befüllt)
    "recipientId": "filters.recipientId",
    "senderId": "filters.senderId",
    "assignedToId": "filters.assignedToId",
    "bookedById": "filters.bookedById",
    # Button-Groups
    "recordType": "filters.recordType",
    "recordStatus": "filters.recordStatus",
}

# Felder ohne filters.-Prefix
EXTRA_FIELDS = {
    "sortBy": "sortBy",
    "sortOrder": "sortOrder",
    "recordsPerPage": "recordsPerPage",
}

# Felder die <select> Elemente sind (single oder multi)
SELECT_FIELDS = {
    "filterdateperiod",
    "carrierCompanyId",
    "serviceId",
    "jobCategoryId",
    "collectionLocationId",
    "deliveryLocationId",
}

# Felder die <select multiple> sind
MULTI_SELECT_FIELDS = {
    "collectionLocationId",
    "deliveryLocationId",
}

# Felder deren Wert aus einem Hidden-Input kommt (Typeahead)
HIDDEN_FIELDS = {
    "recipientId",
    "senderId",
    "assignedToId",
    "bookedById",
}

# Button-Group Felder (Wert kommt von button.selected)
BUTTON_GROUP_FIELDS = {
    "recordType",
    "recordStatus",
}


class FilterHelper:
    """Parsed die iTrak Controller-Seite und baut den Payload für /listdata."""

    def __init__(self, html: str):
        """
        Nimmt das HTML der Controller-Seite nach dem Login entgegen.
        Parsed alle Filter-Felder und speichert deren aktuelle Werte.
        """
        self.soup = bs(html, "html.parser")
        self.filters = {}  # field_name → aktueller Wert (str oder list)

        self._parse_all_fields()

    def _parse_all_fields(self):
        """Parsed alle bekannten Felder aus dem HTML und speichert die Defaults."""

        for field_name in FILTER_FIELD_MAP:
            if field_name in BUTTON_GROUP_FIELDS:
                self.filters[field_name] = self._parse_button_group(field_name)

            elif field_name in MULTI_SELECT_FIELDS:
                self.filters[field_name] = self._parse_multi_select(field_name)

            elif field_name in SELECT_FIELDS:
                self.filters[field_name] = self._parse_select(field_name)

            elif field_name in HIDDEN_FIELDS:
                self.filters[field_name] = self._parse_hidden(field_name)

            else:
                self.filters[field_name] = self._parse_text_input(field_name)

        # Extra-Felder (Sort, Records per Page)
        sort_input = self.soup.find("input", {"id": "savedSortOption"})
        if sort_input:
            self.filters["sortBy"] = sort_input.get("data-by", "internalJobNumber")
            self.filters["sortOrder"] = sort_input.get("data-order", "DESC")

        rpp_select = self.soup.find("select", {"id": "recordPerPage"})
        if rpp_select:
            selected = rpp_select.find("option", selected=True)
            self.filters["recordsPerPage"] = selected["value"] if selected else "100"

    def _parse_select(self, field_name: str) -> str:
        """Parsed ein <select> und gibt den ausgewählten Wert zurück."""
        select = self.soup.find("select", {"id": field_name})
        if not select:
            select = self.soup.find("select", {"name": field_name})
        if not select:
            return ""

        selected_option = select.find("option", selected=True)
        return selected_option["value"] if selected_option else ""

    def _parse_multi_select(self, field_name: str) -> list:
        """Parsed ein <select multiple> und gibt alle ausgewählten Werte als Liste zurück."""
        select = self.soup.find("select", {"id": field_name})
        if not select:
            select = self.soup.find("select", {"name": field_name})
        if not select:
            return []

        selected_options = select.find_all("option", selected=True)
        return [opt["value"] for opt in selected_options]

    def _parse_text_input(self, field_name: str) -> str:
        """Parsed ein <input type='text'> und gibt den Wert zurück."""
        inp = self.soup.find("input", {"id": field_name})
        if not inp:
            inp = self.soup.find("input", {"name": field_name})
        return inp.get("value", "") if inp else ""

    def _parse_hidden(self, field_name: str) -> str:
        """Parsed ein <input type='hidden'> und gibt den Wert zurück."""
        inp = self.soup.find("input", {"id": field_name})
        if not inp:
            inp = self.soup.find("input", {"name": field_name})
        return inp.get("value", "") if inp else ""

    def _parse_button_group(self, field_name: str) -> str:
        """Parsed eine Button-Group und gibt den Wert des 'selected' Buttons zurück."""
        group = self.soup.find("div", {"id": field_name})
        if not group:
            return ""

        selected_btn = group.find("button", class_="selected")
        return selected_btn.get("data-value", "") if selected_btn else ""

    def get_options(self, field_name: str) -> list[dict]:
        """
        Gibt die verfügbaren Optionen für ein Select-Feld zurück.
        Jede Option ist ein Dict: {"value": "00000009", "label": "UPS"}
        """
        select = self.soup.find("select", {"id": field_name})
        if not select:
            select = self.soup.find("select", {"name": field_name})
        if not select:
            return []

        options = []
        for opt in select.find_all("option"):
            value = opt.get("value", "")
            label = opt.get_text(strip=True)
            if value:  # leere Options überspringen
                options.append({"value": value, "label": label})

        return options

    def set_filter(self, field_name: str, value):
        """
        Setzt einen Filter manuell.
        Für Multi-Selects eine Liste übergeben, für alles andere einen String.
        """
        if field_name not in FILTER_FIELD_MAP and field_name not in EXTRA_FIELDS:
            raise ValueError(
                f"Unbekanntes Feld: '{field_name}'. "
                f"Gültige Felder: {list(FILTER_FIELD_MAP.keys()) + list(EXTRA_FIELDS.keys())}"
            )
        self.filters[field_name] = value

    def build_payload(self) -> dict:
        """
        Baut den Payload für den POST an /listdata.
        Gibt ein Dict zurück, das direkt an session.post(data=...) übergeben werden kann.
        """
        payload = {}

        # Filter-Felder
        for field_name, payload_key in FILTER_FIELD_MAP.items():
            # Bei Multi-Selects ist der Wert eine Liste; requests schickt dann
            # automatisch mehrere Werte (der payload_key endet auf []).
            payload[payload_key] = self.filters.get(field_name, "")

        # Extra-Felder (Sort, Records per Page)
        for field_name, payload_key in EXTRA_FIELDS.items():
            value = self.filters.get(field_name, "")
            if value:
                payload[payload_key] = value

        return payload
