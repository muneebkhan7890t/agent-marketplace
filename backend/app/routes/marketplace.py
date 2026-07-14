from fastapi import APIRouter

router = APIRouter()

# This is a static preview list (used before a business has seeded/queried
# the real `agents` table via /agents). Kept in sync with
# app/routes/agents.py::DEFAULT_AGENTS so the marketplace never shows an
# agent here that doesn't actually exist / work in the backend.


@router.get("/agents")
def get_agents():

    return [
        {
            "id": 1,
            "name": "Customer Support Agent",
            "description": "Classifies emails, drafts human-reviewed replies via a classifier -> specialist -> writer -> QA pipeline.",
            "price": 49,
        },
        {
            "id": 2,
            "name": "Sales Agent",
            "description": "Drafts persuasive, honest replies to inbound sales emails.",
            "price": 99,
        },
        {
            "id": 3,
            "name": "Refund Agent",
            "description": "Triages refund requests with empathy; refund decisions stay human-approved.",
            "price": 59,
        },
        {
            "id": 4,
            "name": "WhatsApp Support Agent",
            "description": "Automatically answers customer WhatsApp messages via the WhatsApp Business Cloud API webhook.",
            "price": 69,
        },
    ]
