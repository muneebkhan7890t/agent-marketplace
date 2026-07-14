from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from app.dependencies import get_db
from app.models.agent_log import AgentLog

router = APIRouter()


@router.get("/")
def get_logs(
    db: Session = Depends(get_db)
):

    return db.query(
        AgentLog
    ).all()