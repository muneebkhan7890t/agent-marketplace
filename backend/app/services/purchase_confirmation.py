"""
services/purchase_confirmation.py
-----------------------------------
Shared logic for "a payment gateway just told us money moved -- now what?"
Used by both the Stripe and Razorpay webhook handlers so the actual
purchase/install/receipt flow isn't duplicated across two files.

Previously, routes/stripe.py's /webhook endpoint verified the Stripe
signature and returned {"received": True, "type": event.type} -- it
never actually recorded the Purchase or installed the Agent for the
business. This is the piece that was missing: webhooks that just
outbound-call the gateway APIs (create_payment_intent, create_order,
etc.) don't know whether the customer actually paid; only the gateway's
webhook push tells you that reliably.
"""

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.agent import Agent
from app.models.business import Business
from app.models.user import User
from app.models.purchase import Purchase
from app.models.installed_agent import InstalledAgent
from app.integrations.sendgrid.service import SendGridService
from app.error_tracking import capture_exception


def confirm_purchase_and_install(
    business_id: int,
    agent_id: int,
    gateway: str,
    gateway_reference: str,
) -> dict:
    """
    Idempotent: safe to call more than once for the same event (gateways
    retry webhooks on anything other than a 2xx response). Records the
    Purchase, installs the Agent for the Business if not already
    installed, and emails a receipt.
    """
    db: Session = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        agent = db.query(Agent).filter(Agent.id == agent_id).first()

        if not business or not agent:
            return {
                "confirmed": False,
                "reason": f"business_id={business_id} or agent_id={agent_id} not found",
            }

        user = db.query(User).filter(User.id == business.user_id).first()

        # Purchase record -- one per gateway_reference, not per webhook retry.
        existing_purchase = db.query(Purchase).filter(
            Purchase.user_id == business.user_id,
            Purchase.agent_id == agent_id,
        ).first()
        if not existing_purchase:
            db.add(Purchase(user_id=business.user_id, agent_id=agent_id, status="paid"))

        # Install (idempotent -- mirrors routes/agents.py::install_agent).
        already_installed = db.query(InstalledAgent).filter(
            InstalledAgent.business_id == business_id,
            InstalledAgent.agent_id == agent_id,
        ).first()
        newly_installed = False
        if not already_installed:
            db.add(InstalledAgent(business_id=business_id, agent_id=agent_id, status="active"))
            newly_installed = True

        db.commit()

        if newly_installed and user and user.email:
            try:
                SendGridService().send_purchase_receipt(
                    to_email=user.email,
                    agent_name=agent.name,
                    monthly_price=agent.monthly_price,
                    business_name=business.business_name,
                )
            except Exception as exc:
                # A failed receipt email should never roll back the purchase --
                # the money already moved and the agent is already installed.
                capture_exception(exc, context={"stage": "send_purchase_receipt", "business_id": business_id})

        return {
            "confirmed": True,
            "gateway": gateway,
            "gateway_reference": gateway_reference,
            "business_id": business_id,
            "agent_id": agent_id,
            "newly_installed": newly_installed,
        }
    finally:
        db.close()
