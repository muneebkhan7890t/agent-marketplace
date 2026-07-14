"""
models/agent_action.py
-----------------------
An "AI action" is something more consequential than drafting a reply --
issuing a Stripe refund, opening a support ticket, etc.

These are never auto-executed. The agent only ever PROPOSES an action here
(status="pending"); a human must approve it from the dashboard before
anything actually happens (mirrors the existing Approve/Reject pattern used
for email replies).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class AgentAction(Base):

    __tablename__ = "agent_actions"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, index=True)

    reply_id = Column(Integer, index=True, nullable=True)   # links back to the email draft that triggered this
    email_id = Column(String, index=True, nullable=True)
    thread_id = Column(String, index=True, nullable=True)

    action_type = Column(String, index=True)   # "refund" | "create_ticket"

    title = Column(String)                     # short human-readable label
    description = Column(Text)                 # why the AI is proposing this

    payload = Column(Text)                     # JSON-encoded proposed parameters (amount, ticket priority, etc.)
    result = Column(Text, nullable=True)       # JSON-encoded outcome once executed

    status = Column(String, default="pending", index=True)  # pending | approved | rejected | executed | failed

    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)