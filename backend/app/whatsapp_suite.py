"""
whatsapp_suite.py
==================
THE WhatsApp module. Every phase lives in this one file so the whole
integration can be read and modified in one place instead of hunting
across a dozen files.

    Phase 1  - MCP Connections     : connect / status / disconnect (per business)
    Phase 2  - AI Agents           : classify -> specialist -> writer pipeline
    Phase 3  - Conversation Memory : rolling per-contact chat history
    Phase 4  - Knowledge Base (RAG): business docs injected into replies
    Phase 5  - Actions              : refund / ticket proposals detected in chat
    Phase 6  - Multi-Agent AI       : WhatsAppManager orchestrates phases 2-5
    Phase 7  - Dashboard            : per-business snapshot
    Phase 8  - Analytics            : volume / category / response-time stats
    Phase 9  - Marketplace          : installable WhatsApp automation playbooks
    Phase 10 - Enterprise           : audit log + per-business rate limiting

The only thing NOT in this file is the raw Meta Graph API HTTP wrapper
(integrations/whatsapp/service.py, ~100 lines of `requests.post` calls) --
that's a pure transport-layer detail, kept separate on purpose, exactly
like every other integration in this codebase (stripe, shopify, etc.).
Everything about WHAT to do with WhatsApp lives here.

Wire-up (already done in main.py):
    from app.whatsapp_suite import router as whatsapp_router
    app.include_router(whatsapp_router, prefix="/whatsapp", tags=["WhatsApp"])
"""

import os
import time
import json
from collections import defaultdict, deque
from datetime import datetime

import requests
from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.integrations.whatsapp.service import WhatsAppService

from app.agents.classifier_agent import EmailClassifierAgent
from app.agents.support_agent import SupportAgent
from app.agents.sales_agent import SalesAgent
from app.agents.refund_agent import RefundAgent
from app.agents.writer_agent import WriterAgent
from app.services.action_detector import ActionDetector
from app.services.knowledge_base import KnowledgeBaseService

GRAPH_BASE = "https://graph.facebook.com/v19.0"
router = APIRouter()


# ==================================================================== #
# Shared models (new tables -- picked up automatically by
# create_tables.py's Base.metadata.create_all(), no migration needed
# since these don't exist yet).
# ==================================================================== #

class WhatsAppMessage(Base):
    """Phase 3 (memory) + Phase 8 (analytics) storage: every inbound and
    outbound WhatsApp message, per business."""
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True)
    contact_number = Column(String, index=True)
    direction = Column(String)          # "in" | "out"
    message_text = Column(Text)
    category = Column(String, nullable=True)       # set on inbound msgs by the classifier
    detected_actions = Column(Text, nullable=True)  # JSON list, set by ActionDetector
    created_at = Column(DateTime, default=datetime.utcnow)


class WhatsAppPlaybookInstall(Base):
    """Phase 9 (marketplace): which businesses have "installed" which
    prebuilt WhatsApp automation playbook."""
    __tablename__ = "whatsapp_playbook_installs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True)
    playbook_id = Column(String, index=True)
    status = Column(String, default="active")
    installed_at = Column(DateTime, default=datetime.utcnow)


class WhatsAppAuditLog(Base):
    """Phase 10 (enterprise): who did what, for compliance/support."""
    __tablename__ = "whatsapp_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, index=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine, tables=[
    WhatsAppMessage.__table__,
    WhatsAppPlaybookInstall.__table__,
    WhatsAppAuditLog.__table__,
])


def _audit(db: Session, business_id: int, user_id, action: str, detail: str = ""):
    db.add(WhatsAppAuditLog(business_id=business_id, user_id=user_id, action=action, detail=detail))
    db.commit()


def _verify_ownership(business_id: int, user_id: int, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


# ==================================================================== #
# PHASE 1 -- MCP Connections
# ==================================================================== #

def _get_service(business_id: int) -> WhatsAppService:
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            raise ValueError(f"Business {business_id} not found")
        if not business.whatsapp_connected:
            raise ValueError(f"WhatsApp not connected for business {business_id}")
        return WhatsAppService(token=business.whatsapp_token, phone_id=business.whatsapp_phone_id)
    finally:
        db.close()


def get_business_id_for_phone_number_id(phone_number_id: str):
    """Route an incoming webhook (which only carries the receiving
    number) back to the business that owns it."""
    db = SessionLocal()
    try:
        business = db.query(Business).filter(
            Business.whatsapp_phone_id == phone_number_id,
            Business.whatsapp_connected == True,  # noqa: E712
        ).first()
        return business.id if business else None
    finally:
        db.close()


def extract_phone_number_id(payload: dict):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            phone_number_id = change.get("value", {}).get("metadata", {}).get("phone_number_id")
            if phone_number_id:
                return phone_number_id
    return None


class WhatsAppConnectBody(BaseModel):
    phone_number: str        # human-readable, e.g. "+92 300 1234567"
    phone_number_id: str     # Meta "Phone Number ID"
    access_token: str        # permanent system-user token


@router.post("/connect")
def whatsapp_connect(
    business_id: int = Query(..., description="Business to connect WhatsApp to"),
    body: WhatsAppConnectBody = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate the credentials against Meta, then save them on the
    business and mark it connected."""
    business = _verify_ownership(business_id, current_user.id, db)

    try:
        resp = requests.get(
            f"{GRAPH_BASE}/{body.phone_number_id}",
            headers={"Authorization": f"Bearer {body.access_token}"},
            params={"fields": "verified_name,display_phone_number"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"Couldn't verify WhatsApp credentials with Meta: {exc}")

    existing = db.query(Business).filter(
        Business.whatsapp_phone_id == body.phone_number_id,
        Business.id != business_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This WhatsApp number is already connected to another business.")

    business.whatsapp_business_number = body.phone_number
    business.whatsapp_phone_id = body.phone_number_id
    business.whatsapp_token = body.access_token
    business.whatsapp_connected = True
    db.commit()
    db.refresh(business)

    _audit(db, business_id, current_user.id, "whatsapp_connect", body.phone_number)

    return {"message": "WhatsApp connected", "phone_number": business.whatsapp_business_number, "meta_info": resp.json()}


@router.get("/status")
def whatsapp_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"whatsapp_connected": business.whatsapp_connected, "phone_number": business.whatsapp_business_number}


@router.post("/disconnect")
def whatsapp_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.whatsapp_business_number = None
    business.whatsapp_phone_id = None
    business.whatsapp_token = None
    business.whatsapp_connected = False
    db.commit()
    _audit(db, business_id, current_user.id, "whatsapp_disconnect")
    return {"message": "WhatsApp disconnected"}


class TextMsg(BaseModel):
    to: str
    message: str


class OrderUpdate(BaseModel):
    to: str
    order_id: str
    status: str
    tracking: str = ""


@router.post("/send")
def send_text(
    body: TextMsg,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    _rate_limit(business_id)
    try:
        result = _get_service(business_id).send_text(body.to, body.message)
        _log_message(business_id, body.to, "out", body.message)
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/order-update")
def order_update(
    body: OrderUpdate,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    _rate_limit(business_id)
    try:
        return _get_service(business_id).send_order_update(body.to, body.order_id, body.status, body.tracking)
    except Exception as e:
        raise HTTPException(500, str(e))


# ==================================================================== #
# PHASE 3 -- Conversation Memory
# ==================================================================== #

MAX_MEMORY_MESSAGES = 6
MAX_CHARS_PER_MESSAGE = 500


def _log_message(business_id: int, contact_number: str, direction: str, text: str, category: str = None, actions: list = None):
    db = SessionLocal()
    try:
        db.add(WhatsAppMessage(
            business_id=business_id,
            contact_number=contact_number,
            direction=direction,
            message_text=text,
            category=category,
            detected_actions=json.dumps(actions) if actions else None,
        ))
        db.commit()
    finally:
        db.close()


def build_memory_context(business_id: int, contact_number: str) -> dict:
    """Phase 3: pull the last few messages with this contact so the
    Writer doesn't repeat itself or contradict an earlier reply."""
    db = SessionLocal()
    try:
        rows = (
            db.query(WhatsAppMessage)
            .filter(WhatsAppMessage.business_id == business_id, WhatsAppMessage.contact_number == contact_number)
            .order_by(WhatsAppMessage.created_at.desc())
            .limit(MAX_MEMORY_MESSAGES)
            .all()
        )
        rows.reverse()
        lines = []
        for m in rows:
            speaker = "Business" if m.direction == "out" else "Customer"
            body = (m.message_text or "")[:MAX_CHARS_PER_MESSAGE]
            lines.append(f"{speaker}: {body}")
        return {"history_text": "\n".join(lines), "message_count": len(rows)}
    finally:
        db.close()


@router.get("/memory")
def get_memory(
    business_id: int = Query(...),
    contact_number: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return build_memory_context(business_id, contact_number)


# ==================================================================== #
# PHASE 2 + 4 + 5 + 6 -- AI Agents / Knowledge Base / Actions / Manager
# ==================================================================== #

class WhatsAppManager:
    """Phase 6: orchestrates the classifier, the right specialist, the
    knowledge base, the action detector, and the writer -- the full
    multi-agent pipeline for one WhatsApp message."""

    def __init__(self):
        self.classifier = EmailClassifierAgent()               # Phase 2
        self.specialists = {                                    # Phase 2
            "support": SupportAgent(),
            "sales": SalesAgent(),
            "refund": RefundAgent(),
        }
        self.writer = WriterAgent()                             # Phase 2
        self.knowledge = KnowledgeBaseService()                 # Phase 4
        self.action_detector = ActionDetector()                 # Phase 5

    def build_reply(self, business_id: int, contact_number: str, message_text: str) -> dict:
        memory = build_memory_context(business_id, contact_number)          # Phase 3
        classification = self.classifier.classify(message_text)              # Phase 2
        category, route = classification["category"], classification["route"]

        specialist = self.specialists[route]
        brief = specialist.build_brief(message_text, memory["history_text"])

        # Phase 4: pull relevant knowledge-base chunks into the brief
        try:
            kb_hits = self.knowledge.search(business_id, message_text)
            if kb_hits:
                brief["checklist"] = (brief.get("checklist", "") + "\n\nRelevant business info:\n" +
                                       "\n".join(h["content"] for h in kb_hits))
        except Exception:
            pass  # no KB configured yet -- degrade gracefully

        reply_text = self.writer.write(
            subject="WhatsApp message",
            email_text=message_text,
            history_text=memory["history_text"],
            template=brief.get("role_prompt", ""),
            brief=brief,
        )

        # Phase 5: detect any concrete action implied by this message
        try:
            actions = self.action_detector.detect(message_text, category)
        except Exception:
            actions = []

        return {"category": category, "routed_to": route, "reply_text": reply_text, "actions": actions}

    def handle_message(self, business_id: int, from_number: str, message_text: str) -> dict:
        _log_message(business_id, from_number, "in", message_text)
        result = self.build_reply(business_id, from_number, message_text)

        send_result = _get_service(business_id).send_text(from_number, result["reply_text"])
        _log_message(business_id, from_number, "out", result["reply_text"], category=result["category"], actions=result["actions"])

        result["sent_to"] = from_number
        result["whatsapp_response"] = send_result
        return result

    def handle_webhook_payload(self, payload: dict) -> list:
        results = []
        phone_number_id = extract_phone_number_id(payload)
        business_id = get_business_id_for_phone_number_id(phone_number_id) if phone_number_id else None

        if business_id is None:
            return [{"error": f"No connected business found for phone_number_id={phone_number_id}"}]

        _rate_limit(business_id)

        for msg in WhatsAppService.parse_incoming(payload):
            if not msg.get("from") or not msg.get("text"):
                continue
            try:
                results.append(self.handle_message(business_id, msg["from"], msg["text"]))
            except Exception as exc:
                results.append({"sent_to": msg.get("from"), "error": str(exc)})
        return results


_manager = WhatsAppManager()


@router.post("/agent/reply")
def agent_reply(
    body: TextMsg,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger the full multi-agent pipeline for one message --
    useful for testing without going through the Meta webhook."""
    _verify_ownership(business_id, current_user.id, db)
    try:
        return _manager.handle_message(business_id, body.to, body.message)
    except Exception as e:
        raise HTTPException(500, str(e))


# ==================================================================== #
# Webhook -- one endpoint serves every connected business
# ==================================================================== #

@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == os.getenv("WHATSAPP_VERIFY_TOKEN", ""):
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Forbidden")


@router.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()
    messages = WhatsAppService.parse_incoming(payload)
    agent_replies = _manager.handle_webhook_payload(payload)
    return {"received": len(messages), "messages": messages, "agent_replies": agent_replies}


# ==================================================================== #
# PHASE 7 -- Dashboard
# ==================================================================== #

@router.get("/dashboard")
def whatsapp_dashboard(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)

    total = db.query(WhatsAppMessage).filter(WhatsAppMessage.business_id == business_id).count()
    inbound = db.query(WhatsAppMessage).filter(WhatsAppMessage.business_id == business_id, WhatsAppMessage.direction == "in").count()
    contacts = db.query(WhatsAppMessage.contact_number).filter(WhatsAppMessage.business_id == business_id).distinct().count()
    recent = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.business_id == business_id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "connected": business.whatsapp_connected,
        "phone_number": business.whatsapp_business_number,
        "total_messages": total,
        "inbound_messages": inbound,
        "unique_contacts": contacts,
        "recent_messages": [
            {
                "contact": m.contact_number,
                "direction": m.direction,
                "text": (m.message_text or "")[:120],
                "category": m.category,
                "at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in recent
        ],
    }


# ==================================================================== #
# PHASE 8 -- Analytics
# ==================================================================== #

@router.get("/analytics")
def whatsapp_analytics(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)

    rows = db.query(WhatsAppMessage).filter(WhatsAppMessage.business_id == business_id).all()

    by_category = defaultdict(int)
    by_direction = defaultdict(int)
    by_day = defaultdict(int)
    response_times = []

    inbound_by_contact = defaultdict(list)
    outbound_by_contact = defaultdict(list)

    for m in rows:
        by_direction[m.direction] += 1
        if m.category:
            by_category[m.category] += 1
        if m.created_at:
            by_day[m.created_at.strftime("%Y-%m-%d")] += 1
        (inbound_by_contact if m.direction == "in" else outbound_by_contact)[m.contact_number].append(m.created_at)

    # crude response-time estimate: pair each inbound msg with the next outbound to the same contact
    for contact, in_times in inbound_by_contact.items():
        out_times = sorted(t for t in outbound_by_contact.get(contact, []) if t)
        for t_in in sorted(t for t in in_times if t):
            nxt = next((t for t in out_times if t > t_in), None)
            if nxt:
                response_times.append((nxt - t_in).total_seconds())

    avg_response_seconds = round(sum(response_times) / len(response_times), 1) if response_times else None

    return {
        "total_messages": len(rows),
        "by_direction": dict(by_direction),
        "by_category": dict(by_category),
        "messages_per_day": dict(sorted(by_day.items())),
        "avg_response_seconds": avg_response_seconds,
    }


# ==================================================================== #
# PHASE 9 -- Marketplace (installable WhatsApp playbooks)
# ==================================================================== #

PLAYBOOK_CATALOG = [
    {"id": "order_status_bot", "name": "Order Status Auto-Reply", "description": "Instantly answers 'where is my order' messages using your store's order data."},
    {"id": "faq_bot", "name": "FAQ Responder", "description": "Answers common questions straight from your Knowledge Base."},
    {"id": "abandoned_cart", "name": "Abandoned Cart Nudge", "description": "Sends a friendly follow-up template to customers who didn't finish checkout."},
    {"id": "refund_triage", "name": "Refund Triage", "description": "Classifies refund requests and drafts a response for your approval."},
    {"id": "lead_qualifier", "name": "Sales Lead Qualifier", "description": "Asks qualifying questions to new inbound leads before handing off to a human."},
]


@router.get("/marketplace/playbooks")
def list_playbooks(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    installed_ids = {
        row.playbook_id for row in
        db.query(WhatsAppPlaybookInstall).filter(
            WhatsAppPlaybookInstall.business_id == business_id,
            WhatsAppPlaybookInstall.status == "active",
        ).all()
    }
    return [{**p, "installed": p["id"] in installed_ids} for p in PLAYBOOK_CATALOG]


@router.post("/marketplace/install")
def install_playbook(
    playbook_id: str = Query(...),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    if playbook_id not in {p["id"] for p in PLAYBOOK_CATALOG}:
        raise HTTPException(404, "Unknown playbook")

    existing = db.query(WhatsAppPlaybookInstall).filter(
        WhatsAppPlaybookInstall.business_id == business_id,
        WhatsAppPlaybookInstall.playbook_id == playbook_id,
    ).first()
    if existing:
        existing.status = "active"
    else:
        db.add(WhatsAppPlaybookInstall(business_id=business_id, playbook_id=playbook_id, status="active"))
    db.commit()
    _audit(db, business_id, current_user.id, "playbook_install", playbook_id)
    return {"message": f"{playbook_id} installed"}


@router.post("/marketplace/uninstall")
def uninstall_playbook(
    playbook_id: str = Query(...),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    row = db.query(WhatsAppPlaybookInstall).filter(
        WhatsAppPlaybookInstall.business_id == business_id,
        WhatsAppPlaybookInstall.playbook_id == playbook_id,
    ).first()
    if row:
        row.status = "inactive"
        db.commit()
    _audit(db, business_id, current_user.id, "playbook_uninstall", playbook_id)
    return {"message": f"{playbook_id} uninstalled"}


# ==================================================================== #
# PHASE 10 -- Enterprise (audit log + per-business rate limiting)
# ==================================================================== #

RATE_LIMIT_MAX = 60          # messages
RATE_LIMIT_WINDOW = 60       # seconds
_rate_buckets: dict = defaultdict(lambda: deque())


def _rate_limit(business_id: int):
    """Simple sliding-window limiter so one runaway business can't
    exhaust the shared Meta rate limit for everyone else."""
    now = time.time()
    bucket = _rate_buckets[business_id]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX:
        raise HTTPException(429, "WhatsApp rate limit exceeded for this business, try again shortly.")
    bucket.append(now)


@router.get("/enterprise/audit-log")
def get_audit_log(
    business_id: int = Query(...),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    rows = (
        db.query(WhatsAppAuditLog)
        .filter(WhatsAppAuditLog.business_id == business_id)
        .order_by(WhatsAppAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {"action": r.action, "detail": r.detail, "user_id": r.user_id, "at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]
