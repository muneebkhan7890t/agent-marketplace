"""
agents/order_inventory_agent.py
----------------------------------
Order & Inventory Agent -- sellable marketplace agent built on top of the
Shopify/WooCommerce integration code that already existed but wasn't
attached to anything a customer could install. Two jobs:

  1. Order status replies -- "where is order #1234 / what's in it" ->
     a natural-language reply, without a human having to open Shopify.
  2. Low-stock alerts -- a plain-English summary of what's about to run
     out, for the merchant (not the end customer).

Paste -> backend/app/agents/order_inventory_agent.py
"""

from app.mcp import shopify as shopify_mcp
from app.mcp import woocommerce as woo_mcp
from app.ai.huggingface_client import generate_response


class OrderInventoryAgent:

    role_prompt = "You are a concise, accurate order-status assistant for an ecommerce store."

    def _active_store(self, business):
        """A business can have Shopify, WooCommerce, both, or neither connected."""
        if getattr(business, "shopify_connected", False):
            return "shopify"
        if getattr(business, "woo_connected", False):
            return "woocommerce"
        return None

    # ------------------------------------------------------------------ #
    # Order status
    # ------------------------------------------------------------------ #

    def answer_order_status(self, business, order_id) -> dict:
        store = self._active_store(business)
        if not store:
            return {"error": "No Shopify or WooCommerce store connected for this business."}

        if store == "shopify":
            order = shopify_mcp.get_order(business.id, int(order_id))
        else:
            order = woo_mcp.get_order(business.id, int(order_id))

        if not order:
            return {"error": f"Order {order_id} not found."}

        prompt = f"""
A customer is asking about the status of their order. Here is the raw
order data:
{order}

Write a short, friendly 2-3 sentence reply covering: current status,
what's in the order (if items are listed), and expected next step. Do
not invent a tracking number or delivery date if one isn't present in
the data -- say "we'll notify you once it ships" instead.
"""
        reply_text = generate_response(prompt)
        return {"order": order, "reply": reply_text.strip()}

    # ------------------------------------------------------------------ #
    # Low-stock alerts
    # ------------------------------------------------------------------ #

    def check_low_stock(self, business, threshold: int = None) -> dict:
        store = self._active_store(business)
        if not store:
            return {"error": "No Shopify or WooCommerce store connected for this business."}

        threshold = threshold or getattr(business, "shopify_low_stock_threshold", 5) or 5

        if store == "shopify":
            low_stock = shopify_mcp.get_low_stock_products(business.id, threshold=threshold)
        else:
            low_stock = woo_mcp.get_low_stock_products(business.id, threshold=threshold)

        if not low_stock:
            return {"store": store, "threshold": threshold, "low_stock_products": [], "summary": "Nothing is low on stock."}

        names = [p.get("title") or p.get("name", "Unknown product") for p in low_stock]
        prompt = f"""
These products are running low on stock (threshold: {threshold} units):
{names}

Write a 1-2 sentence alert for the merchant summarizing what needs
restocking soon. Be direct, no fluff.
"""
        summary = generate_response(prompt)
        return {"store": store, "threshold": threshold, "low_stock_products": low_stock, "summary": summary.strip()}
