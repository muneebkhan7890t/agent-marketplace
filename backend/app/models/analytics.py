"""
models/analytics.py
--------------------
Paste → backend/app/models/analytics.py

These tables store pre-aggregated daily/monthly metrics so the
analytics endpoints are fast — no expensive COUNT queries at runtime.
The analytics service populates them; routes just read them.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Date
from datetime import datetime
from app.database import Base


class DailyAnalytics(Base):
    """One row per business per day — aggregated by the scheduler."""
    __tablename__ = "daily_analytics"

    id          = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), index=True)
    date        = Column(Date, index=True)

    # Communication
    emails_received     = Column(Integer, default=0)
    emails_processed    = Column(Integer, default=0)
    ai_replies_sent     = Column(Integer, default=0)
    human_replies       = Column(Integer, default=0)
    failed_replies      = Column(Integer, default=0)
    whatsapp_received   = Column(Integer, default=0)
    whatsapp_sent       = Column(Integer, default=0)
    whatsapp_ai_replies = Column(Integer, default=0)

    # AI Performance
    avg_response_time_sec = Column(Float, default=0)
    approval_rate         = Column(Float, default=0)   # 0-100
    rejection_rate        = Column(Float, default=0)
    avg_reply_length      = Column(Float, default=0)   # words
    ai_confidence_avg     = Column(Float, default=0)   # 0-100

    # Categories
    support_count  = Column(Integer, default=0)
    sales_count    = Column(Integer, default=0)
    refund_count   = Column(Integer, default=0)
    shipping_count = Column(Integer, default=0)
    other_count    = Column(Integer, default=0)

    # Revenue (from Shopify/WooCommerce)
    orders_count      = Column(Integer, default=0)
    revenue_total     = Column(Float, default=0)
    refunds_count     = Column(Integer, default=0)
    refunds_total     = Column(Float, default=0)
    cancelled_count   = Column(Integer, default=0)
    avg_order_value   = Column(Float, default=0)

    # AI Savings
    conversations_automated = Column(Integer, default=0)
    hours_saved             = Column(Float, default=0)
    estimated_salary_saved  = Column(Float, default=0)

    # Actions
    refunds_created  = Column(Integer, default=0)
    tickets_created  = Column(Integer, default=0)
    orders_cancelled = Column(Integer, default=0)
    coupons_issued   = Column(Integer, default=0)

    # Human Review
    approved_replies = Column(Integer, default=0)
    rejected_replies = Column(Integer, default=0)
    edited_replies   = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentMetrics(Base):
    """Daily performance per agent per business."""
    __tablename__ = "agent_metrics"

    id          = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), index=True)
    agent_name  = Column(String, index=True)   # "Email Agent", "Refund Agent" etc.
    date        = Column(Date, index=True)

    actions_taken   = Column(Integer, default=0)
    success_count   = Column(Integer, default=0)
    failure_count   = Column(Integer, default=0)
    avg_latency_sec = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class CustomerMetrics(Base):
    """Rolling customer interaction stats per business."""
    __tablename__ = "customer_metrics"

    id          = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), index=True)
    customer_email = Column(String, index=True)

    total_messages    = Column(Integer, default=0)
    first_contact     = Column(DateTime, nullable=True)
    last_contact      = Column(DateTime, nullable=True)
    categories_seen   = Column(Text, nullable=True)   # JSON list
    is_returning      = Column(Integer, default=0)    # 0/1

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LiveActivityLog(Base):
    """
    Rolling live activity feed — last 200 events per business.
    Written by the agent pipeline; read by /analytics/live.
    """
    __tablename__ = "live_activity"

    id          = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), index=True)
    event_type  = Column(String)   # email_replied, refund_created, order_shipped …
    description = Column(Text)
    agent_name  = Column(String, nullable=True)
    channel     = Column(String, nullable=True)   # email, whatsapp, shopify …
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)
