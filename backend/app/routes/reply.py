"""
routes/reply.py
---------------
Endpoints for human review, approval, and manual sending of AI-generated replies.
"""

import json

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.models.reply import Reply
from app.services.reply_service import ReplyService
from app.services.conversation_memory import ConversationMemory
from app.mcp.gmail import send_email

router = APIRouter()


class EditReplyBody(BaseModel):
    reply_text: str


def _get_owned_business(business_id: int, current_user: User, db: Session) -> Business:
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


def _get_owned_reply(reply_id: int, current_user: User, db: Session) -> Reply:
    reply = db.query(Reply).filter(Reply.id == reply_id).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")

    business = db.query(Business).filter(
        Business.id == reply.business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=403, detail="Forbidden")

    return reply


# ------------------------------------------------------------------ #
# List pending drafts
# ------------------------------------------------------------------ #

@router.get("/pending")
def get_pending_replies(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all AI-generated drafts awaiting human review."""
    _get_owned_business(business_id, current_user, db)

    service = ReplyService()
    return service.get_pending_replies(business_id)


# ------------------------------------------------------------------ #
# Multi-agent pipeline trace behind a draft
# ------------------------------------------------------------------ #

@router.get("/{reply_id}/trace")
def get_reply_trace(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the step-by-step record of how the multi-agent pipeline
    (Classifier -> Specialist -> Writer -> QA) produced this draft.
    """
    reply = _get_owned_reply(reply_id, current_user, db)

    if not reply.agent_trace:
        return {"trace": None}

    return {"trace": json.loads(reply.agent_trace)}


# ------------------------------------------------------------------ #
# Conversation memory: full thread behind a draft
# ------------------------------------------------------------------ #

@router.get("/{reply_id}/thread")
def get_reply_thread(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the full Gmail conversation (oldest -> newest) that this draft
    reply belongs to, so a human reviewer can see the whole back-and-forth
    before approving/sending -- not just the single latest message.
    """
    reply = _get_owned_reply(reply_id, current_user, db)

    if not reply.thread_id:
        return {"thread_id": None, "message_count": 0, "messages": []}

    context = ConversationMemory().build_context(
        business_id=reply.business_id,
        thread_id=reply.thread_id,
    )

    return {
        "thread_id": reply.thread_id,
        "message_count": context["message_count"],
        "messages": [
            {
                "from": m.get("from"),
                "date": m.get("date"),
                "subject": m.get("subject"),
                "body": m.get("body") or m.get("snippet"),
            }
            for m in context["messages"]
        ],
    }


# ------------------------------------------------------------------ #
# Edit a draft
# ------------------------------------------------------------------ #

@router.put("/{reply_id}")
def edit_reply(
    reply_id: int,
    body: EditReplyBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Overwrite the draft text before approving/sending."""
    reply = _get_owned_reply(reply_id, current_user, db)

    reply.reply_text = body.reply_text
    db.commit()
    db.refresh(reply)

    return {"reply_id": reply.id, "reply_text": reply.reply_text}


# ------------------------------------------------------------------ #
# Discard a draft
# ------------------------------------------------------------------ #

@router.delete("/{reply_id}")
def discard_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a draft without sending it."""
    reply = _get_owned_reply(reply_id, current_user, db)

    db.delete(reply)
    db.commit()

    return {"reply_id": reply_id, "discarded": True}


# ------------------------------------------------------------------ #
# Approve + send
# ------------------------------------------------------------------ #

@router.post("/{reply_id}/send")
def send_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send the (possibly edited) draft via Gmail, then mark it approved+sent."""
    reply = _get_owned_reply(reply_id, current_user, db)

    if reply.sent:
        raise HTTPException(status_code=400, detail="This reply has already been sent")

    try:
        send_email(
            business_id=reply.business_id,
            to_email=reply.to_email,
            subject=reply.subject if (reply.subject or "").lower().startswith("re:") else f"Re: {reply.subject or ''}",
            body=reply.reply_text,
            reply_to_msg_id=reply.email_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to send via Gmail: {exc}")

    ReplyService().approve_and_send(reply_id, reply.business_id)

    return {"reply_id": reply.id, "to": reply.to_email, "sent": True}
