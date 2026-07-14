"""
routes/shopify.py
-----------------
Shopify OAuth install flow + data endpoints.

Paste location: backend/app/routes/shopify.py
Then add to main.py:
    from app.routes.shopify import router as shopify_router
    app.include_router(shopify_router, prefix="/shopify", tags=["Shopify"])
"""

import secrets
import requests
import os
from fastapi import Request
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.integrations.shopify.auth import (
    build_auth_url,
    verify_hmac,
    register_order_webhooks,
    SHOPIFY_API_KEY,
    SHOPIFY_API_SECRET,
)
from app.mcp.shopify import get_orders, get_products, get_low_stock_products, get_customers

router = APIRouter()

_oauth_state: dict = {}   # state → business_id  (use Redis in production)

REDIRECT_URI = os.getenv("SHOPIFY_REDIRECT_URI", "http://localhost:8000/shopify/callback")


# ------------------------------------------------------------------ #
# 1. Install / Connect
# ------------------------------------------------------------------ #

@router.get("/connect")
def shopify_connect(
    shop: str = Query(..., description="e.g. mystore.myshopify.com"),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    state = secrets.token_urlsafe(32)
    _oauth_state[state] = {"business_id": business_id, "shop": shop}

    url = build_auth_url(shop=shop, state=state, redirect_uri=REDIRECT_URI)
    return RedirectResponse(url)


# ------------------------------------------------------------------ #
# 2. Callback
# ------------------------------------------------------------------ #

from fastapi import Request

@router.get("/callback")
def shopify_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    # Get ALL query parameters sent by Shopify
    params = dict(request.query_params)

    # Validate required parameters
    shop = params.get("shop")
    code = params.get("code")
    state = params.get("state")

    if not shop or not code or not state:
        raise HTTPException(status_code=400, detail="Missing required Shopify parameters")

    if state not in _oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Verify Shopify HMAC
    if not verify_hmac(params):
        raise HTTPException(status_code=400, detail="HMAC verification failed")

    entry = _oauth_state.pop(state)
    business_id = entry["business_id"]

    # Exchange authorization code for access token
    response = requests.post(
        f"https://{shop}/admin/oauth/access_token",
        json={
            "client_id": SHOPIFY_API_KEY,
            "client_secret": SHOPIFY_API_SECRET,
            "code": code,
        },
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get Shopify access token: {response.text}"
        )

    access_token = response.json().get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="Shopify did not return an access token"
        )

    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.shopify_store_url = shop
    business.shopify_access_token = access_token
    business.shopify_connected = True
    db.commit()

    webhook_results = register_order_webhooks(shop, access_token)

    return {
        "message": "Shopify connected successfully",
        "shop": shop,
        "business_id": business_id,
        "webhooks": webhook_results,
    }


# ------------------------------------------------------------------ #
# 3. Status
# ------------------------------------------------------------------ #

@router.get("/status")
def shopify_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"shopify_connected": business.shopify_connected, "shop": business.shopify_store_url}


# ------------------------------------------------------------------ #
# 4. Data endpoints
# ------------------------------------------------------------------ #

@router.get("/orders")
def shopify_orders(
    business_id: int = Query(...),
    status: str = Query(default="any"),
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"orders": get_orders(business_id, status=status, limit=limit)}


@router.get("/products")
def shopify_products(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"products": get_products(business_id)}


@router.get("/low-stock")
def shopify_low_stock(
    business_id: int = Query(...),
    threshold: int = Query(default=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"low_stock_products": get_low_stock_products(business_id, threshold)}


@router.get("/customers")
def shopify_customers(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"customers": get_customers(business_id)}


# ------------------------------------------------------------------ #
# 5. Disconnect
# ------------------------------------------------------------------ #

@router.post("/disconnect")
def shopify_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.shopify_access_token = None
    business.shopify_store_url    = None
    business.shopify_connected    = False
    db.commit()
    return {"message": "Shopify disconnected"}


# ------------------------------------------------------------------ #
# Helper
# ------------------------------------------------------------------ #

def _verify_ownership(business_id: int, user_id: int, db: Session):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business