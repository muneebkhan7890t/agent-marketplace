"""
models/support_ticket.py
--------------------------
A lightweight internal ticket record, created when an "AI action" of type
create_ticket is approved and executed. Works standalone (no external
service required); if the business has HubSpot connected, the same ticket
is also mirrored into HubSpot (see services/ai_actions.py).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class SupportTicket(Base):

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, index=True)
    action_id = Column(Integer, index=True, nullable=True)   # the AgentAction that created it
    email_id = Column(String, index=True, nullable=True)
    thread_id = Column(String, index=True, nullable=True)

    customer_email = Column(String)
    subject = Column(String)
    summary = Column(Text)
    priority = Column(String, default="normal")   # low | normal | high | urgent
    status = Column(String, default="open")       # open | in_progress | closed

    hubspot_ticket_id = Column(String, nullable=True)  # set if mirrored to HubSpot

    created_at = Column(DateTime, default=datetime.utcnow)