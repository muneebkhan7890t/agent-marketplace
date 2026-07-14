# Shopify A-to-Z Automation — what was added & how to turn it on

## What this does
The moment a customer places an order on a connected Shopify store, the
backend now automatically:
1. Checks the ordered items' stock.
2. Emails the customer an order confirmation (via their connected Gmail).
3. WhatsApps the customer the same confirmation (via their connected WhatsApp).
4. If any ordered SKU just crossed the low-stock threshold, alerts the
   **merchant** (you) by email + WhatsApp — "this product will be less in
   store" - so you know to reorder.
5. Every 30 minutes, it also re-scans the whole catalog for low stock
   (catches stock changed by hand in Shopify admin, not just through orders).
6. Everything is logged to `agent_logs`, visible in the existing `/logs` dashboard.

No admin approval step is required for these (unlike refunds/tickets,
which stay human-approved) — this pipeline only sends notifications, it
never touches money or inventory.

## New / changed files
- `backend/app/services/shopify_automation.py` — the pipeline itself
- `backend/app/routes/shopify_webhooks.py` — receives Shopify's push events
- `backend/app/integrations/shopify/auth.py` — added webhook HMAC check +
  auto-registration
- `backend/app/routes/shopify.py` — registers webhooks right after OAuth connect
- `backend/app/scheduler/scheduler.py` — added the 30-min low-stock sweep
- `backend/app/models/business.py` + `migrate_add_shopify_automation_fields.py`
  — new columns: `shopify_low_stock_threshold`, `owner_alert_whatsapp`, `owner_alert_email`
- `backend/app/routes/business.py` + `schemas/business_schema.py` — new
  `PATCH /businesses/{id}/automation-settings` endpoint

## Setup steps
1. **Run the migration once:**
   ```
   cd backend/app
   python migrate_add_shopify_automation_fields.py
   ```
2. **Set `SHOPIFY_WEBHOOK_BASE_URL` in `.env`** to a public URL Shopify can
   reach — a placeholder was appended for you (`http://localhost:8000`,
   won't work as-is). In dev, run `ngrok http 8000` and put that ngrok
   URL there; in production, use your real domain.
3. **Tell it where to send YOUR alerts** (not the customer's — those come
   from the order automatically):
   ```
   PATCH /businesses/{business_id}/automation-settings
   {
     "owner_alert_whatsapp": "+92XXXXXXXXXX",
     "shopify_low_stock_threshold": 5
   }
   ```
   If you skip `owner_alert_email`, it falls back to the business's own
   connected Gmail address automatically.
4. **(Re)connect Shopify** — `GET /shopify/connect?...` → the OAuth
   callback now auto-registers the `orders/create`, `orders/paid`, and
   `inventory_levels/update` webhooks for you. If a store was connected
   *before* this change, just reconnect once so the webhooks get created.

## Things worth knowing
- The pipeline degrades gracefully: if a business hasn't connected Gmail
  or WhatsApp yet, that channel is just skipped (logged, not fatal) — the
  order still gets processed.
- Webhook signature verification uses the raw request body (required by
  Shopify) — don't add body-parsing middleware in front of that route.
- This intentionally does **not** auto-cancel or auto-refund orders when
  stock runs out — it only alerts you. Wiring that up is a natural next
  step but is a "spend money" action, which this codebase's existing
  pattern (`AgentAction`, pending → approved) treats as something a human
  should confirm, not something that fires silently.
