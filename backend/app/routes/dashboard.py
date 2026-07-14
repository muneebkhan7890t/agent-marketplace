from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.business import Business
from app.models.purchase import Purchase
from app.models.installed_agent import InstalledAgent

router = APIRouter()


@router.get("/")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    businesses = db.query(Business).filter(
        Business.user_id == current_user.id
    ).all()

    purchases = db.query(Purchase).filter(
        Purchase.user_id == current_user.id
    ).all()

    business_ids = [b.id for b in businesses]

    installed_agents = db.query(
        InstalledAgent
    ).filter(
        InstalledAgent.business_id.in_(business_ids)
    ).all()

    return {
        "businesses": businesses,
        "purchases": purchases,
        "installed_agents": installed_agents
    }