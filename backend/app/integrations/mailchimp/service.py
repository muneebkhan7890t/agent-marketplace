"""
integrations/mailchimp/service.py
-----------------------------------
Mailchimp email marketing integration.
Paste → backend/app/integrations/mailchimp/service.py

Env vars:
  MAILCHIMP_API_KEY    ← from Mailchimp Account → Extras → API Keys
  MAILCHIMP_SERVER     ← prefix e.g. "us21" (part of your API key after the dash)
"""

import os
import hashlib
import requests


class MailchimpService:

    def __init__(self):
        self.api_key = os.getenv("MAILCHIMP_API_KEY", "")
        server = os.getenv("MAILCHIMP_SERVER") or (self.api_key.split("-")[-1] if "-" in self.api_key else "us1")
        self.base = f"https://{server}.api.mailchimp.com/3.0"
        self.auth = ("anystring", self.api_key)

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{self.base}{path}", auth=self.auth, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{self.base}{path}", auth=self.auth, json=data)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, data: dict) -> dict:
        r = requests.put(f"{self.base}{path}", auth=self.auth, json=data)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, data: dict) -> dict:
        r = requests.patch(f"{self.base}{path}", auth=self.auth, json=data)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _subscriber_hash(email: str) -> str:
        return hashlib.md5(email.lower().encode()).hexdigest()

    # ── Lists / Audiences ─────────────────────────────────────────────

    def get_lists(self) -> list:
        data = self._get("/lists", {"count": 20})
        return data.get("lists", [])

    def get_list(self, list_id: str) -> dict:
        return self._get(f"/lists/{list_id}")

    def get_list_members(self, list_id: str, status: str = "subscribed", count: int = 50) -> list:
        data = self._get(f"/lists/{list_id}/members", {"status": status, "count": count})
        return data.get("members", [])

    # ── Subscribers ───────────────────────────────────────────────────

    def subscribe(self, list_id: str, email: str, first_name: str = "", last_name: str = "", tags: list = None) -> dict:
        data = {
            "email_address": email,
            "status":        "subscribed",
            "merge_fields":  {"FNAME": first_name, "LNAME": last_name},
        }
        if tags:
            data["tags"] = tags
        subscriber_hash = self._subscriber_hash(email)
        return self._put(f"/lists/{list_id}/members/{subscriber_hash}", data)

    def unsubscribe(self, list_id: str, email: str) -> dict:
        subscriber_hash = self._subscriber_hash(email)
        return self._patch(f"/lists/{list_id}/members/{subscriber_hash}", {"status": "unsubscribed"})

    def add_tags(self, list_id: str, email: str, tags: list) -> dict:
        subscriber_hash = self._subscriber_hash(email)
        tag_data = [{"name": t, "status": "active"} for t in tags]
        return self._post(f"/lists/{list_id}/members/{subscriber_hash}/tags", {"tags": tag_data})

    # ── Campaigns ─────────────────────────────────────────────────────

    def get_campaigns(self, count: int = 10) -> list:
        data = self._get("/campaigns", {"count": count, "sort_field": "create_time", "sort_dir": "DESC"})
        return data.get("campaigns", [])

    def create_campaign(self, list_id: str, subject: str, from_name: str, reply_to: str, preview_text: str = "") -> dict:
        return self._post("/campaigns", {
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject,
                "preview_text": preview_text,
                "from_name":    from_name,
                "reply_to":     reply_to,
            },
        })

    def set_campaign_content(self, campaign_id: str, html: str) -> dict:
        return self._put(f"/campaigns/{campaign_id}/content", {"html": html})

    def send_campaign(self, campaign_id: str) -> dict:
        r = requests.post(f"{self.base}/campaigns/{campaign_id}/actions/send", auth=self.auth)
        r.raise_for_status()
        return {"status": "sent", "campaign_id": campaign_id}

    def schedule_campaign(self, campaign_id: str, schedule_time: str) -> dict:
        """schedule_time: ISO-8601 UTC e.g. '2025-08-01T10:00:00+00:00'"""
        return self._post(f"/campaigns/{campaign_id}/actions/schedule", {"schedule_time": schedule_time})

    # ── Reports ───────────────────────────────────────────────────────

    def get_campaign_report(self, campaign_id: str) -> dict:
        return self._get(f"/reports/{campaign_id}")

    def get_all_reports(self, count: int = 10) -> list:
        data = self._get("/reports", {"count": count})
        return data.get("reports", [])

    # ── Automations ───────────────────────────────────────────────────

    def trigger_automation(self, workflow_id: str, email: str) -> dict:
        """Manually add a subscriber to an automation workflow."""
        return self._post(
            f"/automations/{workflow_id}/emails",
            {"email_address": email},
        )