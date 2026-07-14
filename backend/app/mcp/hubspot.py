"""
mcp/hubspot.py
Paste → backend/app/mcp/hubspot.py  (replaces existing empty file)
"""
from app.integrations.hubspot.service import HubSpotService
_hs = None
def _h(): global _hs; _hs = _hs or HubSpotService(); return _hs

def get_contacts(limit: int = 20) -> list:                          return _h().get_contacts(limit)
def create_contact(email: str, firstname: str = "", lastname: str = "", phone: str = "") -> dict:
    return _h().create_contact(email, firstname, lastname, phone)
def upsert_contact(email: str, properties: dict) -> dict:           return _h().upsert_contact(email, properties)
def search_contacts(query: str) -> list:                             return _h().search_contacts(query)
def create_deal(name: str, amount: float, stage: str = "appointmentscheduled") -> dict:
    return _h().create_deal(name, amount, stage)
def get_deals(limit: int = 20) -> list:                              return _h().get_deals(limit)
def create_note(body: str, contact_id: str = None) -> dict:          return _h().create_note(body, contact_id)