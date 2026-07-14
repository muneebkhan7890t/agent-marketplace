from pydantic import BaseModel
from typing import Optional

class BusinessCreate(BaseModel):

    business_name: str

    industry: str

    website_url: str


class AutomationSettings(BaseModel):
    """Where the Shopify automation pipeline sends alerts, and the
    low-stock threshold that triggers them."""

    owner_alert_whatsapp: Optional[str] = None   # e.g. "+923001234567"
    owner_alert_email: Optional[str] = None       # optional; falls back to connected Gmail
    shopify_low_stock_threshold: Optional[int] = None