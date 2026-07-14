"""
services/reply_service.py
-------------------------
Persistence layer for AI-generated email drafts (Reply rows).
"""

import json

from app.database import SessionLocal
from app.models.reply import Reply


class ReplyService:

    def save_reply(
        self,
        business_id: int,
        email_id: str,
        to_email: str,
        subject: str,
        reply_text: str,
        category: str = "General",
        thread_id: str = None,
    ) -> dict:
        """Persist a new draft reply and return a clean dict."""
        db = SessionLocal()
        try:
            reply = Reply(
                business_id=business_id,
                email_id=email_id,
                thread_id=thread_id,
                to_email=to_email,
                subject=subject,
                reply_text=reply_text,
                category=category,
                approved=False,
                sent=False,
            )
            db.add(reply)
            db.commit()
            db.refresh(reply)

            return {
                "reply_id": reply.id,
                "business_id": reply.business_id,
                "email_id": reply.email_id,
                "thread_id": reply.thread_id,
                "to_email": reply.to_email,
                "subject": reply.subject,
                "category": reply.category,
                "reply_text": reply.reply_text,
                "approved": reply.approved,
                "sent": reply.sent,
                "created_at": str(reply.created_at),
            }
        finally:
            db.close()

    def set_agent_trace(self, reply_id: int, trace_json: str) -> None:
        """Attach the multi-agent pipeline's trace to an already-saved reply."""
        db = SessionLocal()
        try:
            reply = db.query(Reply).filter(Reply.id == reply_id).first()
            if reply:
                reply.agent_trace = trace_json
                db.commit()
        finally:
            db.close()

    def get_pending_replies(self, business_id: int) -> list:
        """Return all unapproved/unsent drafts for a business."""
        db = SessionLocal()
        try:
            rows = db.query(Reply).filter(
                Reply.business_id == business_id,
                Reply.approved == False,
                Reply.sent == False,
            ).order_by(Reply.created_at.desc()).all()

            return [
                {
                    "reply_id": r.id,
                    "email_id": r.email_id,
                    "thread_id": r.thread_id,
                    "to_email": r.to_email,
                    "subject": r.subject,
                    "category": r.category,
                    "reply_text": r.reply_text,
                    "agent_trace": json.loads(r.agent_trace) if r.agent_trace else None,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
        finally:
            db.close()

    def approve_and_send(self, reply_id: int, business_id: int) -> dict:
        """Mark a reply as approved + sent (call after sending via Gmail API)."""
        db = SessionLocal()
        try:
            reply = db.query(Reply).filter(
                Reply.id == reply_id,
                Reply.business_id == business_id,
            ).first()

            if not reply:
                return {"error": "Reply not found"}

            reply.approved = True
            reply.sent = True
            db.commit()
            db.refresh(reply)

            return {"reply_id": reply.id, "sent": reply.sent, "approved": reply.approved}
        finally:
            db.close()
