"""
routes/mailchimp.py
Paste → backend/app/routes/mailchimp.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.mcp import mailchimp as mc

router = APIRouter()

class SubscribeBody(BaseModel):
    list_id: str; email: str; first: str = ""; last: str = ""
    tags: list = []

class CampaignBody(BaseModel):
    list_id: str; subject: str; from_name: str; reply_to: str

class SendBody(BaseModel):
    campaign_id: str

@router.get("/lists")
def lists():
    try:    return {"lists": mc.get_lists()}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/subscribe")
def subscribe(body: SubscribeBody):
    try:    return mc.subscribe(body.list_id, body.email, body.first, body.last, body.tags or None)
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/unsubscribe")
def unsubscribe(list_id: str, email: str):
    try:    return mc.unsubscribe(list_id, email)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/campaigns")
def campaigns(count: int = 10):
    try:    return {"campaigns": mc.get_campaigns(count)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/campaigns")
def create_campaign(body: CampaignBody):
    try:    return mc.create_campaign(body.list_id, body.subject, body.from_name, body.reply_to)
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/campaigns/{campaign_id}/send")
def send_campaign(campaign_id: str):
    try:    return mc.send_campaign(campaign_id)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/reports/{campaign_id}")
def report(campaign_id: str):
    try:    return mc.get_campaign_report(campaign_id)
    except Exception as e: raise HTTPException(500, str(e))


