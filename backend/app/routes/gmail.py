"""
routes/gmail.py
---------------
Gmail OAuth2 flow + status endpoints.

Flow:
  1. Frontend calls GET /gmail/connect?business_id=<id>
     → redirects user to Google OAuth consent screen
  2. Google redirects back to GET /gmail/callback?code=...&state=<business_id>
     → tokens stored on Business row, gmail_connected = True
  3. Frontend can poll GET /gmail/status?business_id=<id> to confirm
  4. GET /gmail/emails?business_id=<id>  → live inbox preview
  5. POST /gmail/disconnect?business_id=<id>  → revoke & clear tokens
"""

import secrets
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.integrations.gmail.auth import create_flow
from app.mcp.gmail import read_emails

router = APIRouter()

# In-memory state store: state_token → {business_id, flow}
# For production: use Redis with a short TTL
_oauth_state: dict = {}


# ------------------------------------------------------------------ #
# 1. Initiate OAuth
# ------------------------------------------------------------------ #

@router.get("/connect")
def gmail_connect(
    business_id: int = Query(..., description="Business to connect Gmail to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start the Gmail OAuth2 flow for the given business.
    Returns a redirect to Google's consent screen.
    """
    # Verify the business belongs to this user
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    state = secrets.token_urlsafe(32)
    flow = create_flow()

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    # Persist flow + business_id keyed by state
    _oauth_state[state] = {"business_id": business_id, "flow": flow}

    return {
    "auth_url": auth_url
}


# ------------------------------------------------------------------ #
# 2. OAuth Callback
# ------------------------------------------------------------------ #

@router.get("/callback")
def gmail_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Google redirects here after the user grants (or denies) consent.
    Stores tokens on the Business row.
    """
    if state not in _oauth_state:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please start the connection again.",
        )

    entry = _oauth_state.pop(state)
    business_id = entry["business_id"]
    flow = entry["flow"]

    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange OAuth code: {exc}",
        )

    credentials = flow.credentials

    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.gmail_access_token = credentials.token
    business.gmail_refresh_token = credentials.refresh_token
    business.gmail_connected = True
    db.commit()
    db.refresh(business)

    return {
        "message": "Gmail connected successfully",
        "business_id": business.id,
        "business_name": business.business_name,
        "gmail_connected": business.gmail_connected,
    }


# ------------------------------------------------------------------ #
# 3. Status check
# ------------------------------------------------------------------ #

@router.get("/status")
def gmail_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check whether Gmail is connected for a business."""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return {
        "business_id": business_id,
        "gmail_connected": business.gmail_connected,
    }


# ------------------------------------------------------------------ #
# 4. Live inbox preview
# ------------------------------------------------------------------ #

@router.get("/emails")
def get_emails(
    business_id: int = Query(...),
    max_results: int = Query(default=20, le=100),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return recent emails for the business.
    Requires Gmail to be connected first.
    """
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    if not business.gmail_connected:
        raise HTTPException(
            status_code=400,
            detail="Gmail is not connected for this business. Call /gmail/connect first.",
        )

    try:
        emails = read_emails(
            business_id=business_id,
            max_results=max_results,
            unread_only=unread_only,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gmail API error: {exc}")

    return {
        "business_id": business_id,
        "count": len(emails),
        "emails": emails,
    }


# ------------------------------------------------------------------ #
# 5. Disconnect
# ------------------------------------------------------------------ #

@router.post("/disconnect")
def gmail_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear stored tokens and mark Gmail as disconnected."""
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.gmail_access_token = None
    business.gmail_refresh_token = None
    business.gmail_connected = False
    db.commit()

    return {"message": "Gmail disconnected successfully", "business_id": business_id}
