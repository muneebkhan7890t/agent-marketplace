"""
services/shopify_automation.py
--------------------------------
The "A to Z" Shopify pipeline. This is what turns a raw Shopify webhook
into: check stock -> confirm the order to the customer (email + WhatsApp)
-> warn the owner if something just went low/out of stock.

Called from:
  routes/shopify_webhooks.py   -- real-time, on every order/inventory event
  scheduler/scheduler.py       -- periodic low-stock sweep (catches drift
                                   that a single order webhook wouldn't,
                                   e.g. stock lowered manually in Shopify)

Design notes:
  - Every external send (Gmail, WhatsApp) is wrapped in try/except so one
    missing integration (e.g. business hasn't connected Gmail yet) never
    breaks the rest of the pipeline -- the order still gets processed.
  - Every run writes an AgentLog row so it shows up in the existing
    /logs dashboard alongside the email + WhatsApp agents, instead of
    being an invisible background process.
  - Nothing here invents a new "confirmed" status on the order itself --
    Shopify's own financial_status/fulfillment_status stay the source of
    truth. This just *reacts* to them.
"""

import json
from datetime import datetime

from app.database import SessionLocal
from app.models.business import Business
from app.models.agent_log import AgentLog
from app.integrations.shopify.utils import parse_order, parse_product, is_low_stock
from app.mcp.shopify import get_products
import app.mcp.gmail as gmail_mcp
import app.mcp.whatsapp as whatsapp_mcp


def _log(db, business_id: int, input_text: str, output_text: str):
    db.add(AgentLog(
        business_id=business_id,
        agent_id=None,
        input_text=input_text,
        output_text=output_text,
        created_at=datetime.utcnow(),
    ))
    db.commit()


def _to_whatsapp_number(business: Business, raw_phone: str) -> str | None:
    """Shopify order phones can be missing or oddly formatted; only send
    if we have something usable. Real E.164 normalization should live in
    integrations/whatsapp/utils -- kept minimal here on purpose."""
    if not raw_phone:
        return None
    return raw_phone.strip().replace(" ", "").replace("-", "")


def _notify_customer_order_confirmed(business: Business, order: dict, db):
    """Step: tell the customer their order is confirmed -- email + WhatsApp."""
    customer_email = order.get("customer_email")
    if business.gmail_connected and customer_email:
        try:
            subject = f"Your order #{order['order_number']} is confirmed"
            lines = "\n".join(
                f"  - {i['title']} x{i['quantity']}" for i in order["items"]
            )
            body = (
                f"Hi {order['customer_name'] or 'there'},\n\n"
                f"Thanks for your order! Here's what we've got confirmed:\n\n"
                f"{lines}\n\n"
                f"Total: {order['currency']} {order['total_price']}\n\n"
                f"We'll message you again once it ships.\n"
            )
            gmail_mcp.send_email(business.id, customer_email, subject, body)
            _log(db, business.id,
                 f"order_confirmed_email order={order['order_number']}",
                 f"sent to {customer_email}")
        except Exception as exc:
            _log(db, business.id,
                 f"order_confirmed_email order={order['order_number']}",
                 f"FAILED: {exc}")

    customer_phone = _to_whatsapp_number(business, order.get("customer_phone", ""))
    if business.whatsapp_connected and customer_phone:
        try:
            msg = (
                f"Hi {order['customer_name'] or ''}! Your order #{order['order_number']} "
                f"is confirmed ({order['currency']} {order['total_price']}). "
                f"We'll notify you when it ships."
            )
            whatsapp_mcp.send_text(business.id, customer_phone, msg)
            _log(db, business.id,
                 f"order_confirmed_whatsapp order={order['order_number']}",
                 f"sent to {customer_phone}")
        except Exception as exc:
            _log(db, business.id,
                 f"order_confirmed_whatsapp order={order['order_number']}",
                 f"FAILED: {exc}")


def _notify_owner(business: Business, subject: str, body: str, db, tag: str):
    """Step: tell the merchant something needs their attention (low stock etc.)."""
    email_to = business.owner_alert_email
    if not email_to and business.gmail_connected:
        try:
            email_to = gmail_mcp.get_own_email_address(business.id)
        except Exception:
            email_to = None

    if business.gmail_connected and email_to:
        try:
            gmail_mcp.send_email(business.id, email_to, subject, body)
            _log(db, business.id, f"{tag}_email", f"sent to {email_to}")
        except Exception as exc:
            _log(db, business.id, f"{tag}_email", f"FAILED: {exc}")

    if business.whatsapp_connected and business.owner_alert_whatsapp:
        try:
            whatsapp_mcp.send_text(business.id, business.owner_alert_whatsapp, f"{subject}\n{body}")
            _log(db, business.id, f"{tag}_whatsapp", f"sent to {business.owner_alert_whatsapp}")
        except Exception as exc:
            _log(db, business.id, f"{tag}_whatsapp", f"FAILED: {exc}")


def _check_items_for_low_stock(business: Business, order: dict, db):
    """Step: after an order, see if any of the SKUs just ordered are now
    at/under threshold, and warn the owner if so. This is the 'this
    product will be less in store' trigger."""
    threshold = business.shopify_low_stock_threshold or 5
    try:
        low_stock = get_low_stock_products_by_sku(business.id, {i["sku"] for i in order["items"] if i.get("sku")}, threshold)
    except Exception as exc:
        _log(db, business.id, f"low_stock_check order={order['order_number']}", f"FAILED: {exc}")
        return

    if low_stock:
        lines = "\n".join(f"  - {p['title']} (qty left: see Shopify)" for p in low_stock)
        _notify_owner(
            business,
            subject="Low stock alert",
            body=f"These products just crossed your low-stock threshold ({threshold}):\n\n{lines}",
            db=db,
            tag=f"low_stock_alert order={order['order_number']}",
        )


def get_low_stock_products_by_sku(business_id: int, skus: set, threshold: int) -> list[dict]:
    """Narrow low-stock check to only the SKUs involved in this order
    (cheap) instead of re-scanning the whole catalog on every order."""
    if not skus:
        return []
    products = get_products(business_id, limit=100)
    hits = []
    for p in products:
        for v in p.get("variants", []):
            if v.get("sku") in skus and (v.get("inventory_qty") or 0) <= threshold:
                hits.append(p)
                break
    return hits


# ------------------------------------------------------------------ #
# Public entry points -- called from routes/shopify_webhooks.py
# ------------------------------------------------------------------ #

def handle_order_created(business_id: int, raw_order: dict):
    """
    The full A-to-Z reaction to a new Shopify order:
      1. Parse the order.
      2. Confirm it to the customer (email + WhatsApp).
      3. Check whether it just tipped any item into low stock, and if so,
         alert the owner.
      4. Log everything.
    """
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return

        order = parse_order(raw_order)
        # customer_phone isn't in parse_order's output; Shopify puts it on
        # the order or the nested customer object depending on checkout flow.
        order["customer_phone"] = (
            raw_order.get("phone")
            or (raw_order.get("customer") or {}).get("phone")
            or (raw_order.get("shipping_address") or {}).get("phone")
            or ""
        )

        _log(db, business_id, f"order_created order={order['order_number']}",
             json.dumps({"items": order["items"], "total": order["total_price"]}))

        _notify_customer_order_confirmed(business, order, db)
        _check_items_for_low_stock(business, order, db)
    finally:
        db.close()


def handle_inventory_update(business_id: int, threshold: int = None):
    """
    Reacts to a raw inventory_levels/update webhook. Shopify's inventory
    webhook payload only carries inventory_item_id + new quantity, not
    which product/title that belongs to -- so rather than guess, we just
    re-run the same low-stock sweep used by the scheduler. Slightly more
    API calls than parsing the payload directly, but correct and simple.
    """
    run_low_stock_sweep(business_id, threshold)


def run_low_stock_sweep(business_id: int, threshold: int = None):
    """
    Full catalog low-stock check for one business. Used by:
      - the inventory webhook handler above
      - the periodic scheduler job (catches manual stock edits in Shopify
        admin that don't go through an order at all)
    """
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business or not business.shopify_connected:
            return

        limit = threshold or business.shopify_low_stock_threshold or 5
        try:
            products = get_products(business_id, limit=100)
        except Exception as exc:
            _log(db, business_id, "low_stock_sweep", f"FAILED to fetch products: {exc}")
            return

        low_stock = [p for p in products if is_low_stock(
            {"variants": [{"inventory_quantity": v["inventory_qty"]} for v in p["variants"]]},
            limit,
        )]

        if low_stock:
            lines = "\n".join(f"  - {p['title']}" for p in low_stock)
            _notify_owner(
                business,
                subject=f"Low stock alert ({len(low_stock)} product(s))",
                body=f"These products are at or below your threshold of {limit} units:\n\n{lines}",
                db=db,
                tag="low_stock_sweep",
            )
        else:
            _log(db, business_id, "low_stock_sweep", "no low-stock items")
    finally:
        db.close()


def run_low_stock_sweep_all_businesses():
    """Scheduler entry point: sweep every business that has Shopify connected."""
    db = SessionLocal()
    try:
        business_ids = [
            b.id for b in db.query(Business).filter(Business.shopify_connected == True).all()  # noqa: E712
        ]
    finally:
        db.close()

    for business_id in business_ids:
        try:
            run_low_stock_sweep(business_id)
        except Exception as exc:
            print(f"[shopify_automation] low-stock sweep failed for business {business_id}: {exc}")
