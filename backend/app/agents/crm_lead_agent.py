"""
agents/crm_lead_agent.py
----------------------------
CRM / Lead Follow-up Agent -- HubSpot integration already existed
(create_contact, upsert_contact, create_deal, create_note) but nothing
sellable used it. This agent takes a new lead, scores it, upserts it
into HubSpot, and drafts a follow-up note/message.

Paste -> backend/app/agents/crm_lead_agent.py
"""

from app.mcp import hubspot as hubspot_mcp
from app.ai.huggingface_client import generate_response


class CRMLeadAgent:

    role_prompt = "You are a sales development rep drafting a first follow-up to a new lead."

    def _score_lead(self, lead: dict) -> int:
        """
        Simple, transparent heuristic scoring (0-100) -- not a black box.
        Merchants can see exactly why a lead scored the way it did.
        """
        score = 40  # baseline: any inbound lead is worth something

        if lead.get("phone"):
            score += 15
        if lead.get("company"):
            score += 10
        budget = (lead.get("budget") or "").lower()
        if any(x in budget for x in ["10k", "20k", "50k", "high"]):
            score += 20
        message = (lead.get("message") or "").lower()
        if any(x in message for x in ["urgent", "asap", "this week", "ready to buy", "ready to purchase"]):
            score += 15

        return min(score, 100)

    def process_new_lead(self, business, lead: dict) -> dict:
        """
        lead: {"email": "...", "firstname": "...", "lastname": "...",
               "phone": "...", "company": "...", "budget": "...", "message": "..."}
        """
        email = lead.get("email")
        if not email:
            return {"error": "Lead has no email address"}

        score = self._score_lead(lead)

        hubspot_contact = None
        if getattr(business, "hubspot_connected", False):
            try:
                hubspot_contact = hubspot_mcp.upsert_contact(
                    email=email,
                    properties={
                        "firstname": lead.get("firstname", ""),
                        "lastname": lead.get("lastname", ""),
                        "phone": lead.get("phone", ""),
                        "company": lead.get("company", ""),
                        "lead_score": str(score),
                    },
                )
            except Exception as exc:
                hubspot_contact = {"error": str(exc)}
        else:
            hubspot_contact = "skipped: HubSpot not connected for this business"

        prompt = f"""
Write a short, personalized first-touch follow-up message for this lead:
Name: {lead.get('firstname', 'there')}
Company: {lead.get('company', 'n/a')}
Their message: {lead.get('message', 'no message provided')}
Lead score: {score}/100

2-3 sentences, warm but professional, one clear next step (e.g. book a
call). No generic "I hope this email finds you well."
"""
        follow_up_message = generate_response(prompt).strip()

        note_result = None
        contact_id = None
        if isinstance(hubspot_contact, dict):
            contact_id = hubspot_contact.get("id") or hubspot_contact.get("vid")
        if getattr(business, "hubspot_connected", False) and contact_id:
            try:
                note_result = hubspot_mcp.create_note(
                    body=f"Auto-drafted follow-up (lead score {score}/100):\n\n{follow_up_message}",
                    contact_id=contact_id,
                )
            except Exception as exc:
                note_result = {"error": str(exc)}

        return {
            "lead_score": score,
            "hubspot_contact": hubspot_contact,
            "follow_up_message": follow_up_message,
            "hubspot_note": note_result,
        }
