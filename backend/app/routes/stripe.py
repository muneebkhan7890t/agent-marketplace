"""
routes/stripe.py
Paste → backend/app/routes/stripe.py
"""
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.mcp import stripe as st
from app.services.purchase_confirmation import confirm_purchase_and_install
from app.error_tracking import capture_exception
from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business

router = APIRouter()


def _verify_ownership(business_id: int, user_id: int, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


class PaymentIntent(BaseModel):
    amount_cents: int
    currency: str = "usd"
    customer_id: str = None
    # Carried through as Stripe metadata so the /webhook handler knows
    # which business + agent to install once payment_intent.succeeded fires.
    business_id: int = None
    agent_id: int = None

class RefundBody(BaseModel):
    payment_intent_id: str
    amount_cents: int = None

class CustomerBody(BaseModel):
    email: str
    name: str = ""


# ------------------------------------------------------------------ #
# Connect / status / disconnect -- Stripe runs on the platform's own
# API key (env var), so "connect" here creates a real Stripe Customer
# for this business (proving the credentials work end-to-end) and
# stores the customer id, rather than just flipping a flag.
# ------------------------------------------------------------------ #

@router.post("/connect")
def stripe_connect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    try:
        customer = st.create_customer(email=current_user.email, name=business.business_name or "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Couldn't verify Stripe credentials: {e}")

    business.stripe_customer_id = customer.get("id")
    business.stripe_connected = True
    db.commit()
    return {"message": "Stripe connected", "stripe_customer_id": business.stripe_customer_id}

@router.get("/status")
def stripe_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"stripe_connected": business.stripe_connected, "stripe_customer_id": business.stripe_customer_id}

@router.post("/disconnect")
def stripe_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.stripe_connected = False
    db.commit()
    return {"message": "Stripe disconnected"}


@router.post("/payment-intent")
def create_payment(body: PaymentIntent):
    metadata = {}
    if body.business_id is not None:
        metadata["business_id"] = str(body.business_id)
    if body.agent_id is not None:
        metadata["agent_id"] = str(body.agent_id)
    try:    return st.create_payment_intent(body.amount_cents, body.currency, body.customer_id, metadata)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/failed-payments")
def failed_payments(limit: int = 20):
    try:    return {"failed": st.get_failed_payments(limit)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/refund")
def refund(body: RefundBody):
    try:    return st.create_refund(body.payment_intent_id, body.amount_cents)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/balance")
def balance():
    try:    return st.get_balance()
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/customers")
def customers(limit: int = 20):
    try:    return {"customers": st.list_customers(limit)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/customers")
def create_customer(body: CustomerBody):
    try:    return st.create_customer(body.email, body.name)
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = st.verify_webhook(payload, sig)
    except Exception as e:
        raise HTTPException(400, str(e))

    event_type = event.get("type")
    result = {"received": True, "type": event_type}

    # payment_intent.succeeded is the reliable "money actually moved" signal --
    # this is what confirms the purchase and installs the agent. The earlier
    # /payment-intent endpoint only *requests* payment; it doesn't confirm it.
    if event_type == "payment_intent.succeeded":
        pi = event.get("data", {}).get("object", {})
        metadata = pi.get("metadata", {}) or {}
        business_id = metadata.get("business_id")
        agent_id = metadata.get("agent_id")

        if business_id and agent_id:
            try:
                result["confirmation"] = confirm_purchase_and_install(
                    business_id=int(business_id),
                    agent_id=int(agent_id),
                    gateway="stripe",
                    gateway_reference=pi.get("id", ""),
                )
            except Exception as exc:
                # Never fail the webhook response over a DB/email hiccup --
                # Stripe will retry a non-2xx response, which could double-charge
                # nothing but WILL spam retries. Log it and move on.
                capture_exception(exc, context={"stripe_event": event_type, "payment_intent": pi.get("id")})
                result["confirmation_error"] = str(exc)
        else:
            result["confirmation"] = "skipped: payment_intent metadata missing business_id/agent_id"

    return result