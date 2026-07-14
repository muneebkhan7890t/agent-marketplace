from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.purchase import Purchase

router = APIRouter()


@router.post("/buy")
def buy_agent(
    user_id: int,
    agent_id: int,
    db: Session = Depends(get_db)
):

    purchase = Purchase(
        user_id=user_id,
        agent_id=agent_id,
        status="paid"
    )

    db.add(purchase)
    db.commit()

    return {
        "message": "Agent purchased successfully"
    }