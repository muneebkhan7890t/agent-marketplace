"""
integrations/whatsapp/service.py
---------------------------------
WhatsApp Business Cloud API (Meta) integration.
Paste → backend/app/integrations/whatsapp/service.py

Required env vars:
  WHATSAPP_TOKEN          ← permanent system user token from Meta Business
  WHATSAPP_PHONE_ID       ← phone number ID from WhatsApp Business account
  WHATSAPP_VERIFY_TOKEN   ← any string you set for webhook verification
"""

import os
import requests

BASE = "https://graph.facebook.com/v19.0"
TOKEN    = os.getenv("WHATSAPP_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")


class WhatsAppService:

    def __init__(self, token: str = None, phone_id: str = None):
        self.token    = token or TOKEN
        self.phone_id = phone_id or PHONE_ID
        self.headers  = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type":  "application/json",
        }

    def _post(self, endpoint: str, data: dict) -> dict:
        r = requests.post(f"{BASE}{endpoint}", headers=self.headers, json=data)
        r.raise_for_status()
        return r.json()

    # ── Sending ───────────────────────────────────────────────────────

    def send_text(self, to: str, message: str) -> dict:
        """Send a plain text message."""
        return self._post(f"/{self.phone_id}/messages", {
            "messaging_product": "whatsapp",
            "to":   to,
            "type": "text",
            "text": {"body": message},
        })

    def send_template(self, to: str, template_name: str, lang: str = "en_US", components: list = None) -> dict:
        """Send a pre-approved template message."""
        payload = {
            "messaging_product": "whatsapp",
            "to":   to,
            "type": "template",
            "template": {
                "name":     template_name,
                "language": {"code": lang},
            },
        }
        if components:
            payload["template"]["components"] = components
        return self._post(f"/{self.phone_id}/messages", payload)

    def send_order_update(self, to: str, order_id: str, status: str, tracking: str = "") -> dict:
        """Convenience wrapper — sends a text order status update."""
        msg = f"Hi! Your order #{order_id} is now *{status}*."
        if tracking:
            msg += f"\nTracking: {tracking}"
        return self.send_text(to, msg)

    def send_reply(self, to: str, reply_to_msg_id: str, message: str) -> dict:
        """Reply to a specific message by ID (shows as reply thread)."""
        return self._post(f"/{self.phone_id}/messages", {
            "messaging_product": "whatsapp",
            "to":      to,
            "type":    "text",
            "context": {"message_id": reply_to_msg_id},
            "text":    {"body": message},
        })

    def mark_as_read(self, message_id: str) -> dict:
        return self._post(f"/{self.phone_id}/messages", {
            "messaging_product": "whatsapp",
            "status":     "read",
            "message_id": message_id,
        })

    # ── Webhook helpers ───────────────────────────────────────────────

    @staticmethod
    def parse_incoming(payload: dict) -> list[dict]:
        """
        Parse a webhook payload into a list of clean message dicts.
        Returns: [{from, message_id, type, text, timestamp}]
        """
        messages = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg in value.get("messages", []):
                    messages.append({
                        "from":       msg.get("from"),
                        "message_id": msg.get("id"),
                        "type":       msg.get("type"),
                        "text":       msg.get("text", {}).get("body", ""),
                        "timestamp":  msg.get("timestamp"),
                    })
        return messages