"""
routes/razorpay_webhooks.py
------------------------------
Razorpay had NO webhook endpoint at all before this -- routes/razorpay.py
only wraps outbound calls (create_order, get_payment, refund_payment).
Outbound calls tell you what you asked for; they don't tell you when a
customer actually pays. This endpoint is what Razorpay pushes to when a
payment succeeds, and is the only reliable trigger for "confirm the
purchase and install the agent."

Paste -> backend/app/routes/razorpay_webhooks.py
Wired in main.py:
    from app.routes.razorpay_webhooks import router as razorpay_webhooks_router
    app.include_router(razorpay_webhooks_router, prefix="/razorpay/webhooks", tags=["Razorpay Webhooks"])

Setup: Razorpay Dashboard -> Settings -> Webhooks -> add
    https://<your-domain>/razorpay/webhooks/payment-captured
Subscribe to the `payment.captured` event, and set RAZORPAY_WEBHOOK_SECRET
to the secret shown there (this is DIFFERENT from RAZORPAY_KEY_SECRET).

IMPORTANT: Razorpay signs the RAW request body, same caveat as Shopify's
webhooks -- always read `await request.body()` before anything else
touches/parses it.
"""

import json
from fastapi import APIRouter, Request, HTTPException

from app.integrations.razorpay.service import RazorpayService
from app.services.purchase_confirmation import confirm_purchase_and_install
from app.error_tracking import capture_exception

router = APIRouter()


@router.post("/payment-captured")
async def payment_captured(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not RazorpayService.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event")
    result = {"received": True, "type": event_type}

    if event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment_entity.get("notes", {}) or {}
        business_id = notes.get("business_id")
        agent_id = notes.get("agent_id")

        if business_id and agent_id:
            try:
                result["confirmation"] = confirm_purchase_and_install(
                    business_id=int(business_id),
                    agent_id=int(agent_id),
                    gateway="razorpay",
                    gateway_reference=payment_entity.get("id", ""),
                )
            except Exception as exc:
                capture_exception(exc, context={"razorpay_event": event_type, "payment_id": payment_entity.get("id")})
                result["confirmation_error"] = str(exc)
        else:
            result["confirmation"] = "skipped: payment notes missing business_id/agent_id"

    return result
