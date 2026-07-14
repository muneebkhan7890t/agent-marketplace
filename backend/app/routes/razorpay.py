"""
routes/razorpay.py
Paste → backend/app/routes/razorpay.py
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.mcp import razorpay as rz

router = APIRouter()

class RZOrder(BaseModel):
    amount_paise: int
    currency: str = "INR"
    receipt: str = ""
    # Carried through as Razorpay order "notes" so the webhook handler
    # (routes/razorpay_webhooks.py) knows which business + agent to
    # install once payment.captured fires.
    business_id: int = None
    agent_id: int = None

class JCPayment(BaseModel):
    txn_ref: str
    amount_pkr: int
    mobile: str
    description: str = "AgentHub Payment"

class VerifySig(BaseModel):
    order_id: str
    payment_id: str
    signature: str

@router.post("/order")
def create_order(body: RZOrder):
    notes = {}
    if body.business_id is not None:
        notes["business_id"] = str(body.business_id)
    if body.agent_id is not None:
        notes["agent_id"] = str(body.agent_id)
    try:    return rz.create_order(body.amount_paise, body.currency, body.receipt, notes or None)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    try:    return rz.get_payment(payment_id)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/failed-payments")
def failed(count: int = 20):
    try:    return {"failed": rz.get_failed_payments(count)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/verify-signature")
def verify(body: VerifySig):
    ok = rz.verify_signature(body.order_id, body.payment_id, body.signature)
    return {"valid": ok}

@router.post("/jazzcash/pay")
def jc_pay(body: JCPayment):
    try:    return rz.jazzcash_pay(body.txn_ref, body.amount_pkr, body.mobile, body.description)
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/jazzcash/inquiry")
def jc_inquiry(txn_ref: str = Query(...)):
    try:    return rz.jazzcash_inquiry(txn_ref)
    except Exception as e: raise HTTPException(500, str(e))