"""Outlook Helper — Verbindet sich mit der laufenden Outlook-Instanz via pywin32."""

import win32com.client


class OutlookHelper:
    """Stellt eine Verbindung zur aktiven Outlook-Instanz her und bietet Zugriff auf gängige Ordner."""

    # Outlook OlDefaultFolders Konstanten
    FOLDER_INBOX = 6
    FOLDER_SENT = 5
    FOLDER_DRAFTS = 16
    FOLDER_CALENDAR = 9
    FOLDER_CONTACTS = 10

    def __init__(self):
        self._app = None
        self._namespace = None
        self._connect()

    def _connect(self):
        """Verbindet sich mit der laufenden Outlook-Instanz."""
        try:
            self._app = win32com.client.Dispatch("Outlook.Application")
            self._namespace = self._app.GetNamespace("MAPI")
        except Exception as e:
            raise ConnectionError(f"Outlook-Verbindung fehlgeschlagen: {e}")

    @property
    def app(self):
        """Die Outlook Application-Instanz."""
        return self._app

    @property
    def namespace(self):
        """Der MAPI Namespace."""
        return self._namespace

    def get_folder(self, folder_id: int):
        """Gibt einen Default-Ordner zurück (z.B. FOLDER_INBOX)."""
        return self._namespace.GetDefaultFolder(folder_id)

    @property
    def inbox(self):
        """Der Posteingang."""
        return self.get_folder(self.FOLDER_INBOX)

    @property
    def sent(self):
        """Gesendete Elemente."""
        return self.get_folder(self.FOLDER_SENT)

    @property
    def drafts(self):
        """Entwürfe."""
        return self.get_folder(self.FOLDER_DRAFTS)

    @property
    def calendar(self):
        """Kalender."""
        return self.get_folder(self.FOLDER_CALENDAR)

    def create_mail(self, to: str = "", subject: str = "", body: str = ""):
        """
        Erstellt eine neue E-Mail (zeigt sie noch nicht an / schickt sie noch nicht).
        Gibt das MailItem zurück, damit man es weiter bearbeiten kann.
        """
        mail = self._app.CreateItem(0)  # 0 = olMailItem
        if to:
            mail.To = to
        if subject:
            mail.Subject = subject
        if body:
            mail.Body = body
        return mail

    def get_recent_mails(self, count: int = 10) -> list:
        """Gibt die letzten N E-Mails aus dem Posteingang zurück."""
        messages = self.inbox.Items
        messages.Sort("[ReceivedTime]", True)  # neueste zuerst

        result = []
        for i, msg in enumerate(messages):
            if i >= count:
                break
            result.append(
                {
                    "subject": msg.Subject,
                    "sender": msg.SenderName,
                    "received": str(msg.ReceivedTime),
                    "unread": msg.UnRead,
                }
            )
        return result
