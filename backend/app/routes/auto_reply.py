from fastapi import APIRouter

from app.services.email_reply import (
    generate_reply
)
from backend import app

router = APIRouter()


@router.post("/")
def auto_reply(
    email_text: str
):

    reply = generate_reply(
        email_text
    )

    return {
        "reply": reply
    }

from app.routes.auto_reply import (
    router as auto_reply_router
)

app.include_router(
    auto_reply_router,
    prefix="/auto-reply",
    tags=["Auto Reply"]
)