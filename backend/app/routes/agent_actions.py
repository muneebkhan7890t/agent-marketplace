"""
routes/agent_actions.py
--------------------------
Execution endpoints for the 7 newly added agents (Order & Inventory,
Abandoned Cart Recovery, Marketing/Ads, CRM/Lead Follow-up, Shipping &
Fulfillment, Reporting, Knowledge Base/FAQ). Each of these already had
its integration code written; this is what actually lets an owner
trigger the agent for a business they own, the same ownership pattern
routes/agents.py::install_agent already uses.

Paste -> backend/app/routes/agent_actions.py
Wired in main.py:
    from app.routes.agent_actions import router as agent_actions_router
    app.include_router(agent_actions_router, prefix="/agent-actions", tags=["Agent Actions"])
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business

from app.agents.order_inventory_agent import OrderInventoryAgent
from app.agents.abandoned_cart_agent import AbandonedCartAgent
from app.agents.marketing_ads_agent import MarketingAdsAgent
from app.agents.crm_lead_agent import CRMLeadAgent
from app.agents.shipping_fulfillment_agent import ShippingFulfillmentAgent
from app.agents.reporting_agent import ReportingAgent
from app.agents.knowledge_faq_agent import KnowledgeFAQAgent

router = APIRouter()


def _get_owned_business(db: Session, business_id: int, current_user: User) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


# ── Order & Inventory Agent ─────────────────────────────────────────────

@router.get("/order-inventory/{business_id}/order/{order_id}")
def order_status(
    business_id: int, order_id: str,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return OrderInventoryAgent().answer_order_status(business, order_id)


@router.get("/order-inventory/{business_id}/low-stock")
def low_stock(
    business_id: int, threshold: int = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return OrderInventoryAgent().check_low_stock(business, threshold=threshold)


# ── Abandoned Cart Recovery Agent ───────────────────────────────────────

@router.post("/abandoned-cart/{business_id}/sweep")
def abandoned_cart_sweep(
    business_id: int, limit: int = 20,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return AbandonedCartAgent().run_recovery_sweep(business, limit=limit)


# ── Marketing/Ads Agent ──────────────────────────────────────────────────

class CampaignBrief(BaseModel):
    objective: str = "drive sales"
    product: str = ""
    audience: str = "general shoppers"
    budget: str = ""


@router.post("/marketing/{business_id}/launch-campaign")
def launch_campaign(
    business_id: int, brief: CampaignBrief,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return MarketingAdsAgent().launch_campaign_from_brief(business, brief.model_dump())


# ── CRM / Lead Follow-up Agent ───────────────────────────────────────────

class NewLead(BaseModel):
    email: str
    firstname: str = ""
    lastname: str = ""
    phone: str = ""
    company: str = ""
    budget: str = ""
    message: str = ""


@router.post("/crm/{business_id}/new-lead")
def process_new_lead(
    business_id: int, lead: NewLead,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return CRMLeadAgent().process_new_lead(business, lead.model_dump())


# ── Shipping & Fulfillment Agent ─────────────────────────────────────────

@router.get("/shipping/{business_id}/track/{tracking_number}")
def track_shipment(
    business_id: int, tracking_number: str, courier: str = None,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return ShippingFulfillmentAgent().answer_where_is_my_order(business, tracking_number, courier)


# ── Reporting Agent ──────────────────────────────────────────────────────

@router.post("/reporting/{business_id}/send-summary")
def send_summary(
    business_id: int,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    business = _get_owned_business(db, business_id, current_user)
    return ReportingAgent().send_summary_to_sheets(business)


# ── Knowledge Base / FAQ Agent ───────────────────────────────────────────
# No ownership check on business here beyond business_id itself being an
# int the caller supplies -- this endpoint is meant to sit behind a public
# chat widget, unlike the others which are owner-only dashboard actions.

class FAQQuestion(BaseModel):
    question: str


@router.post("/faq/{business_id}/ask")
def ask_faq(business_id: int, body: FAQQuestion):
    return KnowledgeFAQAgent().answer(business_id, body.question)
