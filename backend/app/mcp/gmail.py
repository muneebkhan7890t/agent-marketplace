"""
mcp/gmail.py
------------
Top-level MCP layer for Gmail.  All agent code should import from here.
Handles credential hydration + auto-refresh so callers never touch raw tokens.
"""

import base64
from email.mime.text import MIMEText
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from app.database import SessionLocal
from app.models.business import Business
from app.integrations.gmail.utils import parse_message


# ------------------------------------------------------------------ #
# Internal helpers
# ------------------------------------------------------------------ #

def _get_credentials(business: Business) -> Credentials:
    """Build + auto-refresh a Credentials object from stored tokens."""
    creds = Credentials(
        token=business.gmail_access_token,
        refresh_token=business.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )
    return creds


def _refresh_if_needed(creds: Credentials, business: Business, db) -> Credentials:
    """Refresh expired credentials and persist the new access token."""
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        business.gmail_access_token = creds.token
        db.commit()
    return creds


def get_service(business_id: int):
    """
    Return an authenticated Gmail API service for the given business.
    Auto-refreshes the access token if expired.
    """
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            raise ValueError(f"Business {business_id} not found")
        if not business.gmail_connected:
            raise ValueError(f"Business {business_id} has not connected Gmail")

        creds = _get_credentials(business)
        creds = _refresh_if_needed(creds, business, db)

        service = build("gmail", "v1", credentials=creds)
        return service
    finally:
        db.close()


# ------------------------------------------------------------------ #
# Public API used by agents / services
# ------------------------------------------------------------------ #

def read_emails(business_id: int, max_results: int = 20, unread_only: bool = False) -> list[dict]:
    """
    Fetch and parse up to *max_results* emails for the business.
    Returns a list of clean dicts (see integrations/gmail/utils.parse_message).
    """
    service = get_service(business_id)

    kwargs = {"userId": "me", "maxResults": max_results}
    if unread_only:
        kwargs["labelIds"] = ["UNREAD"]

    result = service.users().messages().list(**kwargs).execute()
    raw_messages = result.get("messages", [])

    emails = []
    for msg_ref in raw_messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="full"
        ).execute()
        emails.append(parse_message(msg))

    return emails


def get_email(business_id: int, message_id: str) -> dict:
    """Fetch a single email by ID."""
    service = get_service(business_id)
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    return parse_message(msg)


def get_own_email_address(business_id: int) -> str:
    """
    Return the Gmail address connected for this business.
    Used to tell "the business's own past replies" apart from "the customer's messages"
    when building conversation history.
    """
    service = get_service(business_id)
    profile = service.users().getProfile(userId="me").execute()
    return (profile.get("emailAddress") or "").lower()


def get_thread_messages(business_id: int, thread_id: str) -> list[dict]:
    """
    Fetch every message in a Gmail thread, parsed and sorted oldest -> newest.
    This is the raw material for "conversation memory": instead of only looking
    at the single latest email, the agent can see the whole back-and-forth.
    """
    service = get_service(business_id)
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    raw_messages = thread.get("messages", [])
    parsed = [parse_message(m) for m in raw_messages]

    raw_by_id = {m["id"]: m for m in raw_messages}
    parsed.sort(key=lambda m: int(raw_by_id.get(m["id"], {}).get("internalDate", 0)))
    return parsed


def create_draft(
    business_id: int,
    to_email: str,
    subject: str,
    body: str,
    reply_to_msg_id: str = None,
) -> dict:
    """
    Create a Gmail draft for the business.
    If reply_to_msg_id is provided the draft is threaded as a reply.
    """
    service = get_service(business_id)

    msg = MIMEText(body)
    msg["To"] = to_email
    msg["Subject"] = f"Re: {subject}" if reply_to_msg_id else subject

    thread_id = None
    if reply_to_msg_id:
        original = service.users().messages().get(
            userId="me", id=reply_to_msg_id, format="metadata"
        ).execute()
        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
        msg["In-Reply-To"] = headers.get("Message-Id", "")
        msg["References"] = headers.get("Message-Id", "")
        thread_id = original.get("threadId")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    return service.users().drafts().create(userId="me", body=draft_body).execute()


def send_email(
    business_id: int,
    to_email: str,
    subject: str,
    body: str,
    reply_to_msg_id: str = None,
) -> dict:
    """
    Send an email immediately on behalf of the business.
    """
    service = get_service(business_id)

    msg = MIMEText(body)
    msg["To"] = to_email
    msg["Subject"] = subject

    thread_id = None
    if reply_to_msg_id:
        original = service.users().messages().get(
            userId="me", id=reply_to_msg_id, format="metadata"
        ).execute()
        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
        msg["In-Reply-To"] = headers.get("Message-Id", "")
        msg["References"] = headers.get("Message-Id", "")
        thread_id = original.get("threadId")

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    send_body = {"raw": raw}
    if thread_id:
        send_body["threadId"] = thread_id

    return service.users().messages().send(userId="me", body=send_body).execute()


def mark_as_read(business_id: int, message_id: str):
    service = get_service(business_id)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
