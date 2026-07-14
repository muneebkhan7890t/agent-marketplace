import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build


class GmailService:
    """
    Low-level wrapper around the Gmail REST API.
    Accepts a google.oauth2.credentials.Credentials object.
    """

    def __init__(self, credentials):
        self.service = build("gmail", "v1", credentials=credentials)

    # ------------------------------------------------------------------ #
    # Reading
    # ------------------------------------------------------------------ #

    def list_messages(self, max_results: int = 20, label_ids=None, query: str = ""):
        """Return a list of {id, threadId} dicts."""
        kwargs = {"userId": "me", "maxResults": max_results}
        if label_ids:
            kwargs["labelIds"] = label_ids
        if query:
            kwargs["q"] = query
        result = self.service.users().messages().list(**kwargs).execute()
        return result.get("messages", [])

    def get_message(self, message_id: str, fmt: str = "full"):
        """Return the full message resource."""
        return (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format=fmt)
            .execute()
        )

    def get_thread(self, thread_id: str):
        return (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id)
            .execute()
        )

    # ------------------------------------------------------------------ #
    # Sending / Drafts
    # ------------------------------------------------------------------ #

    def send_email(self, to: str, subject: str, body: str, reply_to_msg_id: str = None):
        """Send an email immediately. Optionally thread it as a reply."""
        msg = MIMEMultipart("alternative")
        msg["To"] = to
        msg["Subject"] = subject

        if reply_to_msg_id:
            original = self.get_message(reply_to_msg_id, fmt="metadata")
            headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
            msg["In-Reply-To"] = headers.get("Message-Id", "")
            msg["References"] = headers.get("Message-Id", "")
            msg["threadId"] = original.get("threadId")

        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body_payload = {"raw": raw}
        if reply_to_msg_id:
            body_payload["threadId"] = original.get("threadId")

        return self.service.users().messages().send(userId="me", body=body_payload).execute()

    def create_draft(self, to: str, subject: str, body: str, reply_to_msg_id: str = None):
        """Create a draft (human review before sending)."""
        msg = MIMEText(body)
        msg["To"] = to
        msg["Subject"] = f"Re: {subject}" if reply_to_msg_id else subject

        if reply_to_msg_id:
            original = self.get_message(reply_to_msg_id, fmt="metadata")
            headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
            msg["In-Reply-To"] = headers.get("Message-Id", "")
            msg["References"] = headers.get("Message-Id", "")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        draft_body = {"message": {"raw": raw}}
        if reply_to_msg_id:
            draft_body["message"]["threadId"] = original.get("threadId")

        return self.service.users().drafts().create(userId="me", body=draft_body).execute()

    # ------------------------------------------------------------------ #
    # Labels
    # ------------------------------------------------------------------ #

    def mark_as_read(self, message_id: str):
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()

    def add_label(self, message_id: str, label_name: str):
        """Add a label by name (creates it if missing)."""
        label_id = self._get_or_create_label(label_name)
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()

    def _get_or_create_label(self, name: str) -> str:
        labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
        for lbl in labels:
            if lbl["name"].lower() == name.lower():
                return lbl["id"]
        new = self.service.users().labels().create(
            userId="me", body={"name": name}
        ).execute()
        return new["id"]
