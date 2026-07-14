"""
routes/woocommerce.py
---------------------
WooCommerce API key setup + data endpoints.

Paste location: backend/app/routes/woocommerce.py
Then add to main.py:
    from app.routes.woocommerce import router as woo_router
    app.include_router(woo_router, prefix="/woocommerce", tags=["WooCommerce"])
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.business import Business
from app.mcp.woocommerce import (
    get_orders, get_order, update_order_status,
    add_order_note, create_refund,
    get_products, get_low_stock_products, update_stock,
    get_customers, get_sales_report,
)

router = APIRouter()


class WooConnectBody(BaseModel):
    store_url:       str    # https://mystore.com
    consumer_key:    str
    consumer_secret: str


class UpdateStockBody(BaseModel):
    product_id: int
    quantity:   int


class OrderNoteBody(BaseModel):
    note:          str
    customer_note: bool = False


class RefundBody(BaseModel):
    amount: str
    reason: str = ""


# ------------------------------------------------------------------ #
# Connect (no OAuth — just save API keys)
# ------------------------------------------------------------------ #

@router.post("/connect")
def woo_connect(
    business_id: int = Query(...),
    body: WooConnectBody = ...,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.woo_store_url       = body.store_url.rstrip("/")
    business.woo_consumer_key    = body.consumer_key
    business.woo_consumer_secret = body.consumer_secret
    business.woo_connected       = True
    db.commit()
    return {"message": "WooCommerce connected", "store_url": body.store_url}


@router.get("/status")
def woo_status(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    return {"woo_connected": business.woo_connected, "store_url": business.woo_store_url}


# ------------------------------------------------------------------ #
# Orders
# ------------------------------------------------------------------ #

@router.get("/orders")
def woo_orders(
    business_id: int = Query(...),
    status: str = Query(default="any"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"orders": get_orders(business_id, status=status)}


@router.get("/orders/{order_id}")
def woo_get_order(
    order_id: int,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return get_order(business_id, order_id)


@router.put("/orders/{order_id}/status")
def woo_update_order_status(
    order_id: int,
    status: str = Query(...),
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return update_order_status(business_id, order_id, status)


@router.post("/orders/{order_id}/note")
def woo_order_note(
    order_id: int,
    body: OrderNoteBody,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return add_order_note(business_id, order_id, body.note, body.customer_note)


@router.post("/orders/{order_id}/refund")
def woo_refund(
    order_id: int,
    body: RefundBody,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return create_refund(business_id, order_id, body.amount, body.reason)


# ------------------------------------------------------------------ #
# Products
# ------------------------------------------------------------------ #

@router.get("/products")
def woo_products(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"products": get_products(business_id)}


@router.get("/low-stock")
def woo_low_stock(
    business_id: int = Query(...),
    threshold: int = Query(default=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return {"low_stock": get_low_stock_products(business_id, threshold)}


@router.put("/products/stock")
def woo_update_stock(
    body: UpdateStockBody,
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return update_stock(business_id, body.product_id, body.quantity)


# ------------------------------------------------------------------ #
# Reports
# ------------------------------------------------------------------ #

@router.get("/reports/sales")
def woo_sales_report(
    business_id: int = Query(...),
    period: str = Query(default="week"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_ownership(business_id, current_user.id, db)
    return get_sales_report(business_id, period)


# ------------------------------------------------------------------ #
# Disconnect
# ------------------------------------------------------------------ #

@router.post("/disconnect")
def woo_disconnect(
    business_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business = _verify_ownership(business_id, current_user.id, db)
    business.woo_consumer_key    = None
    business.woo_consumer_secret = None
    business.woo_connected       = False
    db.commit()
    return {"message": "WooCommerce disconnected"}


def _verify_ownership(business_id: int, user_id: int, db: Session):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id,
    ).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business