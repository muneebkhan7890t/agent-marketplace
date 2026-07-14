"""
routes/meta_ads.py
Paste → backend/app/routes/meta_ads.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.mcp import meta_ads as ma

router = APIRouter()

class CampaignCreate(BaseModel):
    name: str; objective: str; status: str = "PAUSED"; daily_budget: int = None

@router.get("/campaigns")
def campaigns():
    try:    return {"campaigns": ma.get_campaigns()}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/campaigns")
def create(body: CampaignCreate):
    try:    return ma.create_campaign(body.name, body.objective, body.status)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/campaigns/{campaign_id}/insights")
def insights(campaign_id: str, date_preset: str = "last_7d"):
    try:    return ma.get_campaign_insights(campaign_id, date_preset)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/account/insights")
def account_insights(date_preset: str = "last_7d"):
    try:    return ma.get_account_insights(date_preset)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/account/spend")
def spend():
    try:    return ma.get_spend_summary()
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/audiences")
def audiences():
    try:    return {"audiences": ma.get_custom_audiences()}
    except Exception as e: raise HTTPException(500, str(e))


