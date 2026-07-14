import base64
import re
from typing import Optional


def parse_email_headers(headers: list) -> dict:
    """Convert the Gmail headers list to a simple dict."""
    return {h["name"]: h["value"] for h in headers}


def extract_body(payload: dict) -> str:
    """
    Recursively extract plain-text body from a Gmail message payload.
    Handles single-part and multi-part messages.
    """
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            result = extract_body(part)
            if result:
                return result

    return ""


def extract_email_address(raw: str) -> str:
    """Pull the bare email address out of strings like 'Name <email@example.com>'."""
    match = re.search(r"<(.+?)>", raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def parse_message(message: dict) -> dict:
    """
    Convert a raw Gmail message resource into a clean dict
    with the fields our services actually need.
    """
    payload = message.get("payload", {})
    headers = parse_email_headers(payload.get("headers", []))

    return {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "from": headers.get("From", ""),
        "from_email": extract_email_address(headers.get("From", "")),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "snippet": message.get("snippet", ""),
        "body": extract_body(payload),
        "label_ids": message.get("labelIds", []),
    }
