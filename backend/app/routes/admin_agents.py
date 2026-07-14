"""
routes/admin_agents.py
------------------------
Admin-only catalog management. Previously the only way to add, edit, or
remove an agent from the marketplace was to hand-edit DEFAULT_AGENTS in
routes/agents.py and redeploy. This gives an admin full CRUD over the
`agents` table at runtime instead.

Paste -> backend/app/routes/admin_agents.py
Wired in main.py:
    from app.routes.admin_agents import router as admin_agents_router
    app.include_router(admin_agents_router, prefix="/admin/agents", tags=["Admin: Agents"])

Auth: every endpoint requires get_current_admin_user (users.is_admin = TRUE).
See migrate_add_admin_field.py to add that column to an existing database,
then manually flip is_admin = TRUE for yourself.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_admin_user
from app.models.user import User
from app.models.agent import Agent
from app.models.installed_agent import InstalledAgent

router = APIRouter()


class AgentCreateBody(BaseModel):
    name: str
    description: str
    category: str
    monthly_price: float
    status: str = "active"


class AgentUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    monthly_price: Optional[float] = None
    status: Optional[str] = None


# ── List every agent, including inactive/hidden ones ──────────────────────

@router.get("/")
def list_all_agents(
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    return db.query(Agent).order_by(Agent.id.asc()).all()


# ── Create ──────────────────────────────────────────────────────────────

@router.post("/")
def create_agent(
    body: AgentCreateBody,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    existing = db.query(Agent).filter(Agent.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="An agent with that name already exists")

    agent = Agent(
        name=body.name,
        description=body.description,
        category=body.category,
        monthly_price=body.monthly_price,
        status=body.status,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


# ── Update (partial) ───────────────────────────────────────────────────

@router.put("/{agent_id}")
def update_agent(
    agent_id: int,
    body: AgentUpdateBody,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return agent


# ── Toggle active/inactive without a full update ───────────────────────

@router.patch("/{agent_id}/status")
def set_agent_status(
    agent_id: int,
    status: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = status
    db.commit()
    db.refresh(agent)
    return agent


# ── Delete ──────────────────────────────────────────────────────────────

@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    installs = db.query(InstalledAgent).filter(InstalledAgent.agent_id == agent_id).count()
    if installs > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Agent has {installs} active installation(s). "
                    "Set status to 'inactive' instead of deleting, or remove installs first.",
        )

    db.delete(agent)
    db.commit()
    return {"message": "Agent deleted", "agent_id": agent_id}
