from fastapi import APIRouter

from app.agents.customer_support import (
    CustomerSupportAgent
)

router = APIRouter()


@router.post("/analyze")
def analyze_email(
    email_text: str
):

    agent = CustomerSupportAgent()

    reply = agent.process_email(
        email_text
    )

    return {
        "email": email_text,
        "reply": reply
    }
from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.dependencies import get_db

from app.agents.customer_support import (
    CustomerSupportAgent
)

from app.models.agent_log import AgentLog

router = APIRouter()


@router.post("/analyze")
def analyze_email(
    business_id: int,
    email_text: str,
    db: Session = Depends(get_db)
):

    agent = CustomerSupportAgent()

    reply = agent.process_email(
        email_text
    )

    log = AgentLog(
    business_id=business_id,
    agent_id=1,
    input_text=email_text,
    output_text=reply
)

    db.add(log)
    db.commit()

    return {
        "reply": reply
    }