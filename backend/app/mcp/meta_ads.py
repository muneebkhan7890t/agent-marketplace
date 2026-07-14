"""
mcp/meta_ads.py
Paste → backend/app/mcp/meta_ads.py
"""
from app.integrations.meta_ads.service import MetaAdsService
_ma = None
def _a(): global _ma; _ma = _ma or MetaAdsService(); return _ma

def get_campaigns() -> list:                                          return _a().get_campaigns()
def get_account_insights(date_preset: str = "last_7d") -> dict:      return _a().get_account_insights(date_preset)
def get_campaign_insights(campaign_id: str, date_preset: str = "last_7d") -> dict:
    return _a().get_campaign_insights(campaign_id, date_preset)
def get_spend_summary() -> dict:                                      return _a().get_spend_summary()
def create_campaign(name: str, objective: str, status: str = "PAUSED") -> dict:
    return _a().create_campaign(name, objective, status)
def update_campaign_status(campaign_id: str, status: str) -> dict:   return _a().update_campaign_status(campaign_id, status)
def get_custom_audiences() -> list:                                   return _a().get_custom_audiences()