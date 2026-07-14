"""
routes/actions.py
-------------------
Human review layer for "AI actions" (refunds, support tickets) proposed by
the auto-reply pipeline. Nothing in this file executes anything against
Stripe/HubSpot until a human hits Approve -- same pattern as the reply
approve/reject dashboard.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.support_ticket import SupportTicket
from app.services.ai_action import AIActionService

router = APIRouter()


def _get_owned_business(business_id: int, current_user: User, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


class ApproveActionBody(BaseModel):
    payment_intent_id: str = None
    amount_cents: int = None
    priority: str = None


# ------------------------------------------------------------------ #
# List pending AI actions
# ------------------------------------------------------------------ #

@router.get("/pending")
def list_pending_actions(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    return {"actions": AIActionService().list_pending(business_id)}


# ------------------------------------------------------------------ #
# Approve + execute
# ------------------------------------------------------------------ #

@router.post("/{action_id}/approve")
def approve_action(
    action_id: int,
    body: ApproveActionBody,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Approving executes the action immediately (issues the Stripe refund or
    creates the ticket). Pass overrides (e.g. payment_intent_id, amount_cents)
    if the AI's suggestion needs a correction first.
    """
    _get_owned_business(business_id, current_user, db)

    overrides = {k: v for k, v in body.dict().items() if v is not None}
    result = AIActionService().approve_and_execute(action_id, business_id, overrides)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ------------------------------------------------------------------ #
# Reject
# ------------------------------------------------------------------ #

@router.post("/{action_id}/reject")
def reject_action(
    action_id: int,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    result = AIActionService().reject(action_id, business_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ------------------------------------------------------------------ #
# Support tickets created by executed actions
# ------------------------------------------------------------------ #

@router.get("/tickets")
def list_tickets(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_business(business_id, current_user, db)
    rows = db.query(SupportTicket).filter(
        SupportTicket.business_id == business_id
    ).order_by(SupportTicket.created_at.desc()).all()

    return {
        "tickets": [
            {
                "ticket_id": t.id,
                "customer_email": t.customer_email,
                "subject": t.subject,
                "summary": t.summary,
                "priority": t.priority,
                "status": t.status,
                "hubspot_ticket_id": t.hubspot_ticket_id,
                "created_at": str(t.created_at),
            }
            for t in rows
        ]
    }