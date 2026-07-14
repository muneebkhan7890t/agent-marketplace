"""
routes/analytics.py
--------------------
Paste → backend/app/routes/analytics.py

Then add to main.py:
    from app.routes.analytics import router as analytics_router
    app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.services.analytics_service import (
    get_overview,
    get_email_analytics,
    get_ai_performance,
    get_customer_analytics,
    get_category_analytics,
    get_agent_performance,
    get_ai_savings,
    get_actions_analytics,
    get_live_activity,
    get_charts,
    get_ai_score,
)

router = APIRouter()


def _biz_id(business_id: int, current_user: User, db: Session) -> int:
    """Verify the business belongs to this user and return its id."""
    biz = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not biz:
        from fastapi import HTTPException
        raise HTTPException(404, "Business not found")
    return biz.id


# ── Overview ──────────────────────────────────────────────────────────

@router.get("/overview")
def analytics_overview(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    High-level KPIs: today, 30-day totals, AI savings, score.
    Use this to power the main dashboard header.
    """
    bid = _biz_id(business_id, current_user, db)
    return get_overview(db, bid)


# ── Emails ────────────────────────────────────────────────────────────

@router.get("/emails")
def email_analytics(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Email volume, approval rates, daily breakdown, top customers."""
    bid = _biz_id(business_id, current_user, db)
    return get_email_analytics(db, bid, days)


# ── AI Performance ────────────────────────────────────────────────────

@router.get("/ai-performance")
def ai_performance(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approval rate, rejection rate, avg reply length, agent breakdown."""
    bid = _biz_id(business_id, current_user, db)
    return get_ai_performance(db, bid, days)


# ── Customers ─────────────────────────────────────────────────────────

@router.get("/customers")
def customer_analytics(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """New vs returning customers, top customers, engagement stats."""
    bid = _biz_id(business_id, current_user, db)
    return get_customer_analytics(db, bid, days)


# ── Categories ────────────────────────────────────────────────────────

@router.get("/categories")
def category_analytics(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What topics customers ask about most — pie chart data."""
    bid = _biz_id(business_id, current_user, db)
    return get_category_analytics(db, bid, days)


# ── Agent Performance ─────────────────────────────────────────────────

@router.get("/agents")
def agent_analytics(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Which agent worked hardest — leaderboard."""
    bid = _biz_id(business_id, current_user, db)
    return get_agent_performance(db, bid, days)


# ── AI Savings ────────────────────────────────────────────────────────

@router.get("/savings")
def ai_savings(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hours saved, salary saved, FTE equivalent. Best sales tool."""
    bid = _biz_id(business_id, current_user, db)
    return get_ai_savings(db, bid, days)


# ── Actions ───────────────────────────────────────────────────────────

@router.get("/actions")
def actions_analytics(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Refunds created, tickets, cancellations, total AI actions."""
    bid = _biz_id(business_id, current_user, db)
    return get_actions_analytics(db, bid, days)


# ── Live Activity ─────────────────────────────────────────────────────

@router.get("/live")
def live_activity(
    business_id: int = Query(...),
    limit: int = Query(default=30, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real-time feed of the last N agent events."""
    bid = _biz_id(business_id, current_user, db)
    return {"events": get_live_activity(db, bid, limit)}


# ── Charts ────────────────────────────────────────────────────────────

@router.get("/charts")
def charts(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Daily time-series arrays ready to plug into Chart.js / Recharts."""
    bid = _biz_id(business_id, current_user, db)
    return get_charts(db, bid, days)


# ── AI Score ─────────────────────────────────────────────────────────

@router.get("/score")
def ai_score(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Composite AI quality score 0-100 with letter grade."""
    bid = _biz_id(business_id, current_user, db)
    return get_ai_score(db, bid)


# ── Full report (all sections in one call) ────────────────────────────

@router.get("/full-report")
def full_report(
    business_id: int = Query(...),
    days: int = Query(default=30, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All analytics in a single call — use for PDF exports or summary pages."""
    bid = _biz_id(business_id, current_user, db)
    return {
        "overview":        get_overview(db, bid),
        "emails":          get_email_analytics(db, bid, days),
        "ai_performance":  get_ai_performance(db, bid, days),
        "customers":       get_customer_analytics(db, bid, days),
        "categories":      get_category_analytics(db, bid, days),
        "agents":          get_agent_performance(db, bid, days),
        "savings":         get_ai_savings(db, bid, days),
        "actions":         get_actions_analytics(db, bid, days),
        "charts":          get_charts(db, bid, days),
        "ai_score":        get_ai_score(db, bid),
        "live":            get_live_activity(db, bid, 20),
    }
