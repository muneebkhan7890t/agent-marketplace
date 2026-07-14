from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime

from app.database import Base


class Reply(Base):

    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, index=True)

    email_id = Column(String, index=True)

    thread_id = Column(String, index=True, nullable=True)  # Gmail thread this reply belongs to

    to_email = Column(String)

    subject = Column(String)

    reply_text = Column(Text)

    category = Column(String, nullable=True)       # Sales, Support, Refund …

    agent_trace = Column(Text, nullable=True)       # JSON trace of the multi-agent pipeline run

    approved = Column(Boolean, default=False)

    sent = Column(Boolean, default=False)          # track if actually sent

    created_at = Column(DateTime, default=datetime.utcnow)
