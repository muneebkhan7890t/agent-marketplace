"""
integrations/hubspot/service.py
---------------------------------
HubSpot CRM integration (contacts, deals, companies, notes).
Paste → backend/app/integrations/hubspot/service.py

Env vars:
  HUBSPOT_API_KEY   ← Private App access token from HubSpot
"""

import os
import requests

BASE = "https://api.hubapi.com"


class HubSpotService:

    def __init__(self, api_key: str = None):
        self.headers = {
            "Authorization": f"Bearer {api_key or os.getenv('HUBSPOT_API_KEY', '')}",
            "Content-Type":  "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{BASE}{path}", headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{BASE}{path}", headers=self.headers, json=data)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, data: dict) -> dict:
        r = requests.patch(f"{BASE}{path}", headers=self.headers, json=data)
        r.raise_for_status()
        return r.json()

    # ── Contacts ──────────────────────────────────────────────────────

    def get_contacts(self, limit: int = 20) -> list:
        data = self._get("/crm/v3/objects/contacts", {"limit": limit})
        return data.get("results", [])

    def get_contact(self, contact_id: str) -> dict:
        return self._get(f"/crm/v3/objects/contacts/{contact_id}")

    def create_contact(self, email: str, firstname: str = "", lastname: str = "", phone: str = "", properties: dict = None) -> dict:
        props = {"email": email, "firstname": firstname, "lastname": lastname, "phone": phone}
        if properties:
            props.update(properties)
        return self._post("/crm/v3/objects/contacts", {"properties": props})

    def update_contact(self, contact_id: str, properties: dict) -> dict:
        return self._patch(f"/crm/v3/objects/contacts/{contact_id}", {"properties": properties})

    def search_contacts(self, query: str) -> list:
        data = self._post("/crm/v3/objects/contacts/search", {
            "query": query, "limit": 10,
        })
        return data.get("results", [])

    def upsert_contact(self, email: str, properties: dict) -> dict:
        """Create contact or update if email already exists."""
        results = self.search_contacts(email)
        if results:
            contact_id = results[0]["id"]
            return self.update_contact(contact_id, properties)
        return self.create_contact(email=email, **properties)

    # ── Deals ─────────────────────────────────────────────────────────

    def get_deals(self, limit: int = 20) -> list:
        data = self._get("/crm/v3/objects/deals", {"limit": limit})
        return data.get("results", [])

    def create_deal(self, dealname: str, amount: float, stage: str = "appointmentscheduled", pipeline: str = "default") -> dict:
        return self._post("/crm/v3/objects/deals", {"properties": {
            "dealname":  dealname,
            "amount":    str(amount),
            "dealstage": stage,
            "pipeline":  pipeline,
        }})

    def update_deal_stage(self, deal_id: str, stage: str) -> dict:
        return self._patch(f"/crm/v3/objects/deals/{deal_id}", {"properties": {"dealstage": stage}})

    # ── Notes / Activities ────────────────────────────────────────────

    def create_note(self, body: str, contact_id: str = None) -> dict:
        data = self._post("/crm/v3/objects/notes", {"properties": {
            "hs_note_body":      body,
            "hs_timestamp":      str(int(__import__("time").time() * 1000)),
        }})
        if contact_id and data.get("id"):
            self._post(f"/crm/v3/objects/notes/{data['id']}/associations/contacts/{contact_id}/note_to_contact", {})
        return data

    # ── Companies ─────────────────────────────────────────────────────

    def get_companies(self, limit: int = 20) -> list:
        data = self._get("/crm/v3/objects/companies", {"limit": limit})
        return data.get("results", [])

    def create_company(self, name: str, domain: str = "", properties: dict = None) -> dict:
        props = {"name": name, "domain": domain}
        if properties:
            props.update(properties)
        return self._post("/crm/v3/objects/companies", {"properties": props})

    # ── Tickets ───────────────────────────────────────────────────────

    def create_ticket(self, subject: str, content: str, priority: str = "MEDIUM", contact_email: str = None) -> dict:
        """Create a support ticket in HubSpot's default ticket pipeline."""
        props = {
            "subject": subject,
            "content": content,
            "hs_pipeline": "0",
            "hs_pipeline_stage": "1",
            "hs_ticket_priority": priority.upper(),
        }
        ticket = self._post("/crm/v3/objects/tickets", {"properties": props})

        if contact_email and ticket.get("id"):
            contacts = self.search_contacts(contact_email)
            if contacts:
                contact_id = contacts[0]["id"]
                self._post(
                    f"/crm/v3/objects/tickets/{ticket['id']}/associations/contacts/{contact_id}/ticket_to_contact",
                    {},
                )
        return ticket