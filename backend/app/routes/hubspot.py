"""
routes/hubspot.py
Paste → backend/app/routes/hubspot.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.mcp import hubspot as hs   # import from mcp/others.py — rename file to hubspot.py

router = APIRouter()

class ContactBody(BaseModel):
    email: str; firstname: str = ""; lastname: str = ""; phone: str = ""

class DealBody(BaseModel):
    name: str; amount: float; stage: str = "appointmentscheduled"

class NoteBody(BaseModel):
    body: str; contact_id: str = None

@router.get("/contacts")
def contacts(limit: int = 20):
    try:    return {"contacts": hs.get_contacts(limit)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/contacts")
def create_contact(body: ContactBody):
    try:    return hs.create_contact(body.email, body.firstname, body.lastname, body.phone)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/contacts/search")
def search(query: str):
    try:    return {"results": hs.search_contacts(query)}
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/deals")
def deals(limit: int = 20):
    try:    return {"deals": hs.get_deals(limit)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/deals")
def create_deal(body: DealBody):
    try:    return hs.create_deal(body.name, body.amount, body.stage)
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/notes")
def create_note(body: NoteBody):
    try:    return hs.create_note(body.body, body.contact_id)
    except Exception as e: raise HTTPException(500, str(e))


