"""
services/ai_actions.py
------------------------
Turns ActionDetector proposals into pending AgentAction rows, and executes
them ONLY after a human clicks "Approve" in the dashboard -- exactly the
same human-in-the-loop pattern already used for email replies.

Refunds and ticket creation are irreversible / customer-facing, so nothing
here ever fires automatically off an incoming email.
"""

import json
from datetime import datetime

from app.database import SessionLocal
from app.models.agent_action import AgentAction
from app.models.support_ticket import SupportTicket
from app.models.business import Business
from app.services.action_detector import ActionDetector
from app.mcp import stripe as stripe_mcp
from app.mcp import hubspot as hubspot_mcp


class AIActionService:

    def __init__(self):
        self.detector = ActionDetector()

    # ------------------------------------------------------------------ #
    # Propose (called from the auto-reply pipeline, never auto-executes)
    # ------------------------------------------------------------------ #

    def detect_and_propose(
        self,
        business_id: int,
        reply_id: int,
        email_id: str,
        thread_id: str,
        to_email: str,
        subject: str,
        email_text: str,
        category: str,
    ) -> list:
        proposals = self.detector.detect(email_text, category)
        if not proposals:
            return []

        db = SessionLocal()
        created = []
        try:
            for p in proposals:
                if p["type"] == "refund":
                    # Best-effort: try to resolve which Stripe payment this
                    # refers to so the human just has to click "Approve".
                    suggestion = {}
                    try:
                        suggestion = stripe_mcp.find_recent_succeeded_payment_by_email(to_email)
                    except Exception as exc:
                        print(f"[AIActionService] Stripe lookup failed for {to_email}: {exc}")

                    payload = {
                        "reason": p.get("reason"),
                        "requested_amount_cents": p.get("amount_cents"),
                        "customer_email": to_email,
                        "suggested_payment_intent_id": suggestion.get("payment_intent_id"),
                        "suggested_amount_cents": suggestion.get("amount_cents"),
                        "currency": suggestion.get("currency", "usd"),
                    }
                    title = f"Refund for {to_email}"
                    description = p.get("reason") or "Customer requested a refund."

                    action = AgentAction(
                        business_id=business_id,
                        reply_id=reply_id,
                        email_id=email_id,
                        thread_id=thread_id,
                        action_type="refund",
                        title=title,
                        description=description,
                        payload=json.dumps(payload),
                        status="pending",
                    )

                elif p["type"] == "create_ticket":
                    payload = {
                        "customer_email": to_email,
                        "subject": subject,
                        "summary": p.get("summary"),
                        "priority": p.get("priority", "normal"),
                    }
                    action = AgentAction(
                        business_id=business_id,
                        reply_id=reply_id,
                        email_id=email_id,
                        thread_id=thread_id,
                        action_type="create_ticket",
                        title=f"Support ticket: {subject}",
                        description=p.get("summary") or subject,
                        payload=json.dumps(payload),
                        status="pending",
                    )
                else:
                    continue

                db.add(action)
                db.commit()
                db.refresh(action)
                created.append(self._to_dict(action))
        finally:
            db.close()

        return created

    # ------------------------------------------------------------------ #
    # List
    # ------------------------------------------------------------------ #

    def list_pending(self, business_id: int) -> list:
        db = SessionLocal()
        try:
            rows = db.query(AgentAction).filter(
                AgentAction.business_id == business_id,
                AgentAction.status == "pending",
            ).order_by(AgentAction.created_at.desc()).all()
            return [self._to_dict(r) for r in rows]
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # Approve + execute
    # ------------------------------------------------------------------ #

    def approve_and_execute(self, action_id: int, business_id: int, overrides: dict = None) -> dict:
        overrides = overrides or {}
        db = SessionLocal()
        try:
            action = db.query(AgentAction).filter(
                AgentAction.id == action_id,
                AgentAction.business_id == business_id,
            ).first()
            if not action:
                return {"error": "Action not found"}
            if action.status not in ("pending",):
                return {"error": f"Action already {action.status}"}

            payload = json.loads(action.payload or "{}")
            payload.update(overrides)

            try:
                if action.action_type == "refund":
                    result = self._execute_refund(payload)
                elif action.action_type == "create_ticket":
                    result = self._execute_ticket(db, action, payload)
                else:
                    result = {"error": f"Unknown action type {action.action_type}"}

                action.status = "failed" if "error" in result else "executed"
                action.result = json.dumps(result)
                action.executed_at = datetime.utcnow()
                db.commit()

            except Exception as exc:
                action.status = "failed"
                action.result = json.dumps({"error": str(exc)})
                action.executed_at = datetime.utcnow()
                db.commit()

            return self._to_dict(action)
        finally:
            db.close()

    def reject(self, action_id: int, business_id: int) -> dict:
        db = SessionLocal()
        try:
            action = db.query(AgentAction).filter(
                AgentAction.id == action_id,
                AgentAction.business_id == business_id,
            ).first()
            if not action:
                return {"error": "Action not found"}
            action.status = "rejected"
            db.commit()
            return self._to_dict(action)
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # Execution helpers
    # ------------------------------------------------------------------ #

    def _execute_refund(self, payload: dict) -> dict:
        payment_intent_id = payload.get("payment_intent_id") or payload.get("suggested_payment_intent_id")
        if not payment_intent_id:
            return {"error": "No payment_intent_id provided or found -- supply one to approve this refund"}

        amount_cents = (
            payload.get("amount_cents")
            or payload.get("requested_amount_cents")
            or payload.get("suggested_amount_cents")
        )

        refund = stripe_mcp.create_refund(payment_intent_id, amount_cents)
        return {
            "refund_id": refund.get("id"),
            "status": refund.get("status"),
            "amount_cents": refund.get("amount"),
        }

    def _execute_ticket(self, db, action: AgentAction, payload: dict) -> dict:
        ticket = SupportTicket(
            business_id=action.business_id,
            action_id=action.id,
            email_id=action.email_id,
            thread_id=action.thread_id,
            customer_email=payload.get("customer_email"),
            subject=payload.get("subject") or action.title,
            summary=payload.get("summary") or action.description,
            priority=payload.get("priority", "normal"),
            status="open",
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        result = {"ticket_id": ticket.id, "status": "open"}

        # Best-effort mirror into HubSpot if the business has it connected.
        business = db.query(Business).filter(Business.id == action.business_id).first()
        if business and getattr(business, "hubspot_connected", False):
            try:
                hs_ticket = hubspot_mcp.create_ticket(
                    subject=ticket.subject,
                    content=ticket.summary,
                    priority=ticket.priority,
                    contact_email=ticket.customer_email,
                )
                ticket.hubspot_ticket_id = hs_ticket.get("id")
                db.commit()
                result["hubspot_ticket_id"] = hs_ticket.get("id")
            except Exception as exc:
                print(f"[AIActionService] HubSpot ticket sync failed: {exc}")
                result["hubspot_sync_error"] = str(exc)

        return result

    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_dict(action: AgentAction) -> dict:
        return {
            "action_id": action.id,
            "business_id": action.business_id,
            "reply_id": action.reply_id,
            "email_id": action.email_id,
            "thread_id": action.thread_id,
            "action_type": action.action_type,
            "title": action.title,
            "description": action.description,
            "payload": json.loads(action.payload) if action.payload else {},
            "result": json.loads(action.result) if action.result else None,
            "status": action.status,
            "created_at": str(action.created_at),
        }