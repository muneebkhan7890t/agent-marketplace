"""
routes/amazon.py
----------------
Amazon SP-API endpoints.

Paste location: backend/app/routes/amazon.py
Then add to main.py:
    from app.routes.amazon import router as amazon_router
    app.include_router(amazon_router, prefix="/amazon", tags=["Amazon"])
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.mcp.amazon import (
    get_orders, get_order, get_order_items,
    get_inventory, get_low_inventory,
    search_catalog, request_report, get_report_status,
)

router = APIRouter()


# ------------------------------------------------------------------ #
# Connect (just enable the feature flag)
# ------------------------------------------------------------------ #

@router.post("/connect")
def amazon_connect(
    business_id: int = Query(...),
    seller_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.amazon_connected = True
    business.amazon_seller_id = seller_id
    db.commit()
    return {"message": "Amazon enabled", "seller_id": seller_id}


@router.get("/status")
def amazon_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"amazon_connected": business.amazon_connected, "seller_id": business.amazon_seller_id}


# ------------------------------------------------------------------ #
# Orders
# ------------------------------------------------------------------ #

@router.get("/orders")
def amazon_orders(
    business_id: int = Query(...),
    created_after: str = Query(default=None, description="ISO-8601 e.g. 2024-01-01T00:00:00Z"),
    status: str = Query(default=None, description="Unshipped,Shipped,Canceled"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    statuses = status.split(",") if status else None
    return {"orders": get_orders(created_after=created_after, statuses=statuses)}


@router.get("/orders/{order_id}")
def amazon_get_order(
    order_id: str,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return get_order(order_id)


@router.get("/orders/{order_id}/items")
def amazon_order_items(
    order_id: str,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"items": get_order_items(order_id)}


# ------------------------------------------------------------------ #
# Inventory
# ------------------------------------------------------------------ #

@router.get("/inventory")
def amazon_inventory(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"inventory": get_inventory()}


@router.get("/inventory/low-stock")
def amazon_low_inventory(
    business_id: int = Query(...),
    threshold: int = Query(default=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"low_inventory": get_low_inventory(threshold)}


# ------------------------------------------------------------------ #
# Catalog
# ------------------------------------------------------------------ #

@router.get("/catalog/search")
def amazon_catalog_search(
    keywords: str = Query(...),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"results": search_catalog(keywords)}


# ------------------------------------------------------------------ #
# Reports
# ------------------------------------------------------------------ #

@router.post("/reports/request")
def amazon_request_report(
    report_type: str = Query(...),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    report_id = request_report(report_type)
    return {"report_id": report_id}


@router.get("/reports/{report_id}")
def amazon_report_status(
    report_id: str,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return get_report_status(report_id)


# ------------------------------------------------------------------ #
# Disconnect
# ------------------------------------------------------------------ #

@router.post("/disconnect")
def amazon_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.amazon_connected = False
    db.commit()
    return {"message": "Amazon disconnected"}


def _verify_ownership(business_id: int, user_id: int, db: Session):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business