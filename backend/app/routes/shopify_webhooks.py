"""
routes/shopify_webhooks.py
----------------------------
Receives Shopify's push notifications and kicks off the automation
pipeline in services/shopify_automation.py. These are registered
automatically per-business right after OAuth (see
integrations/shopify/auth.register_order_webhooks, called from
routes/shopify.py's /callback).

Paste location: backend/app/routes/shopify_webhooks.py
Wired in main.py:
    from app.routes.shopify_webhooks import router as shopify_webhooks_router
    app.include_router(shopify_webhooks_router, prefix="/shopify/webhooks", tags=["Shopify Webhooks"])

IMPORTANT: Shopify signs the RAW request body. FastAPI's parsed `request.json()`
re-serializes and would NOT match the signature reliably -- always read
`await request.body()` first and verify against those exact bytes.
"""

import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.business import Business
from app.integrations.shopify.auth import verify_webhook_hmac
from app.services.shopify_automation import handle_order_created, handle_inventory_update

router = APIRouter()


def _business_for_shop(shop_domain: str) -> Business | None:
    db: Session = SessionLocal()
    try:
        return db.query(Business).filter(Business.shopify_store_url == shop_domain).first()
    finally:
        db.close()


async def _verify_and_parse(request: Request):
    raw_body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    if not verify_webhook_hmac(raw_body, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    business = _business_for_shop(shop_domain)
    if not business:
        # Shop isn't connected to any business row (or was disconnected) --
        # ack with 200 anyway so Shopify doesn't retry/disable the webhook,
        # but do nothing.
        return None, None

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    return business, payload


@router.post("/orders-create")
async def orders_create(request: Request, background_tasks: BackgroundTasks):
    business, payload = await _verify_and_parse(request)
    if business:
        # Ack Shopify immediately, do the email/WhatsApp/stock-check work
        # in the background -- Shopify times out (and retries/disables)
        # webhooks that take too long to respond.
        background_tasks.add_task(handle_order_created, business.id, payload)
    return {"received": True}


@router.post("/orders-paid")
async def orders_paid(request: Request, background_tasks: BackgroundTasks):
    business, payload = await _verify_and_parse(request)
    if business:
        # Payment confirmation is also a reasonable moment to (re)confirm
        # the order with the customer -- same pipeline as orders/create.
        background_tasks.add_task(handle_order_created, business.id, payload)
    return {"received": True}


@router.post("/inventory_levels-update")
async def inventory_levels_update(request: Request, background_tasks: BackgroundTasks):
    business, payload = await _verify_and_parse(request)
    if business:
        background_tasks.add_task(handle_inventory_update, business.id)
    return {"received": True}
