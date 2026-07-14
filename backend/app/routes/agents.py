from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.agent import Agent
from app.models.installed_agent import InstalledAgent
from app.models.business import Business
from app.schemas.agent import AgentCreate

router = APIRouter()


# ── List Agents ─────────────────────────────────────────────────────────
# NOTE: previously this file defined TWO `@router.get("/")` handlers
# (get_agents and list_agents). FastAPI silently only ever calls the
# first one, which made the second a dead duplicate. Merged into one.

@router.get("/")
def get_agents(
    db: Session = Depends(get_db)
):

    return db.query(Agent).all()


# ── Create Sample / Real Agents (idempotent) ─────────────────────────────
# Previously this endpoint blindly inserted the same 3 agents every time
# it was called, which is how the marketplace ended up with duplicate
# rows ("Customer Support Agent", "Marketing Agent", "Sales Agent" showing
# up multiple times). It now checks for an existing agent by name before
# inserting, and adds the real, working WhatsApp Support Agent (backed by
# app/agents/whatsapp_agent.py + app/mcp/whatsapp.py) to the catalog.

DEFAULT_AGENTS = [
    {
        "name": "Customer Support Agent",
        "description": "Classifies incoming emails, drafts human-reviewed replies, and proposes refunds/tickets via the multi-agent email pipeline (classifier -> specialist -> writer -> QA).",
        "category": "Support",
        "monthly_price": 49,
        "status": "active",
    },
    {
        "name": "Sales Agent",
        "description": "Reads inbound sales emails and drafts persuasive, honest replies without over-promising pricing or features it isn't sure about.",
        "category": "Sales",
        "monthly_price": 99,
        "status": "active",
    },
    {
        "name": "Refund Agent",
        "description": "Triages refund requests with empathy and drafts a reply, while leaving the actual refund decision to a human via the Action Agent approval flow.",
        "category": "Support",
        "monthly_price": 59,
        "status": "active",
    },
    {
        "name": "WhatsApp Support Agent",
        "description": "Answers customer WhatsApp messages automatically using the WhatsApp Business Cloud API webhook + the same classifier/writer pipeline used for email.",
        "category": "Support",
        "monthly_price": 69,
        "status": "active",
    },
    # ── Added: these 7 previously had integration code (Shopify, WooCommerce,
    # Mailchimp, Meta Ads, HubSpot, Shiprocket/TCS/Leopards, Google Sheets,
    # the RAG knowledge base) with nothing sellable wired up to any of it.
    {
        "name": "Order & Inventory Agent",
        "description": "Answers 'where is my order' from live Shopify/WooCommerce data and sends the merchant low-stock alerts before a product actually sells out.",
        "category": "Operations",
        "monthly_price": 59,
        "status": "active",
    },
    {
        "name": "Abandoned Cart Recovery Agent",
        "description": "Finds Shopify checkouts that were started but never completed and sends a short, non-pushy recovery email via Mailchimp/email.",
        "category": "Marketing",
        "monthly_price": 79,
        "status": "active",
    },
    {
        "name": "Marketing/Ads Agent",
        "description": "Turns a short campaign brief into a paused, human-reviewable Meta Ads campaign plus a matching Mailchimp email — drafts copy, doesn't spend money unattended.",
        "category": "Marketing",
        "monthly_price": 89,
        "status": "active",
    },
    {
        "name": "CRM / Lead Follow-up Agent",
        "description": "Scores new leads, upserts them into HubSpot, and drafts a personalized first follow-up message and CRM note.",
        "category": "Sales",
        "monthly_price": 69,
        "status": "active",
    },
    {
        "name": "Shipping & Fulfillment Agent",
        "description": "Answers 'where's my order' using live tracking from whichever courier is connected — Shiprocket, TCS, or Leopards.",
        "category": "Operations",
        "monthly_price": 49,
        "status": "active",
    },
    {
        "name": "Reporting Agent",
        "description": "Pushes a daily/weekly order-and-revenue summary from Shopify/WooCommerce straight into a Google Sheet — no manual exports.",
        "category": "Operations",
        "monthly_price": 39,
        "status": "active",
    },
    {
        "name": "Knowledge Base / FAQ Agent",
        "description": "Answers customer questions directly from your uploaded docs using the RAG knowledge base, with cited sources — drop it into a chat widget or support form on its own.",
        "category": "Support",
        "monthly_price": 45,
        "status": "active",
    },
]


@router.post("/seed")
def seed_agents(
    db: Session = Depends(get_db)
):
    created = []
    skipped = []

    for agent_data in DEFAULT_AGENTS:
        exists = db.query(Agent).filter(
            Agent.name == agent_data["name"]
        ).first()

        if exists:
            skipped.append(agent_data["name"])
            continue

        agent = Agent(**agent_data)
        db.add(agent)
        created.append(agent_data["name"])

    db.commit()

    return {
        "message": "Agents seeded",
        "created": created,
        "skipped_existing": skipped,
    }


@router.post("/dedupe")
def dedupe_agents(
    db: Session = Depends(get_db)
):
    """
    Fixes an already-running database that has duplicate agent rows
    (e.g. from calling /agents/seed multiple times before this file's
    idempotency fix). This is a data fix, not a code fix -- restarting
    the server or updating the code alone does not remove rows that
    already exist in the database, which is why duplicates can persist
    even after this file is updated. Call this once to clean them up.
    """
    all_agents = db.query(Agent).order_by(Agent.id.asc()).all()

    by_name = {}
    for agent in all_agents:
        by_name.setdefault(agent.name, []).append(agent)

    removed_ids = []
    kept = {}
    for name, rows in by_name.items():
        if len(rows) <= 1:
            continue

        keep = rows[0]
        kept[name] = keep.id

        for dup in rows[1:]:
            db.query(InstalledAgent).filter(
                InstalledAgent.agent_id == dup.id
            ).update({InstalledAgent.agent_id: keep.id})
            removed_ids.append(dup.id)
            db.delete(dup)

    db.commit()

    # Also add any of the default agents (incl. WhatsApp Support Agent)
    # that are still completely missing.
    added = []
    for agent_data in DEFAULT_AGENTS:
        exists = db.query(Agent).filter(Agent.name == agent_data["name"]).first()
        if not exists:
            db.add(Agent(**agent_data))
            added.append(agent_data["name"])

    db.commit()

    return {
        "message": "Deduped agents table",
        "removed_duplicate_ids": removed_ids,
        "kept_ids_by_name": kept,
        "added_missing_defaults": added,
    }


# ── Install an Agent ──────────────────────────────────────────────────────

@router.post("/install/{agent_id}")
def install_agent(
    agent_id: int,
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    agent = db.query(Agent).filter(
        Agent.id == agent_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    # Prevent installing the same agent twice for the same business.
    already_installed = db.query(InstalledAgent).filter(
        InstalledAgent.business_id == business.id,
        InstalledAgent.agent_id == agent.id
    ).first()

    if already_installed:
        return {
            "message": "Agent already installed",
            "installed_agent_id": already_installed.id,
        }

    installed = InstalledAgent(
        business_id=business.id,
        agent_id=agent.id,
        status="active"
    )

    db.add(installed)

    db.commit()

    return {
        "message": "Agent installed successfully"
    }


# ── My Installed Agents ───────────────────────────────────────────────────

@router.get("/my-agents")
def my_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    businesses = db.query(Business).filter(
        Business.user_id == current_user.id
    ).all()

    business_ids = [b.id for b in businesses]

    installed = db.query(
        InstalledAgent
    ).filter(
        InstalledAgent.business_id.in_(business_ids)
    ).all()

    return installed


# ── Create a Custom Agent ─────────────────────────────────────────────────

@router.post("/")
def create_agent(
    data: AgentCreate,
    db: Session = Depends(get_db)
):

    # Bug fix: this used to reference `data.price`, a field that doesn't
    # exist on AgentCreate or the Agent model (which uses monthly_price),
    # so this endpoint threw an AttributeError on every call.
    agent = Agent(
        name=data.name,
        description=data.description,
        monthly_price=data.monthly_price,
        category=data.category,
        status=data.status,
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return agent
