"""
agents/shipping_fulfillment_agent.py
----------------------------------------
Shipping & Fulfillment Agent -- answers "where's my order" using
whichever courier integration the business actually has connected
(Shiprocket, TCS, or Leopards -- all three already had working service
code with nothing selling them as a standalone agent).

Paste -> backend/app/agents/shipping_fulfillment_agent.py
"""

from app.mcp import shiprocket as ship_mcp
from app.ai.huggingface_client import generate_response


class ShippingFulfillmentAgent:

    role_prompt = "You are a friendly, accurate shipment-tracking assistant."

    def _track(self, business, tracking_number: str, courier: str = None) -> dict:
        """
        courier: "shiprocket" | "tcs" | "leopards" | None (auto-detect from
        whichever is connected on the business, preferring Shiprocket).
        """
        courier = courier or (
            "shiprocket" if getattr(business, "shiprocket_connected", False) else
            "tcs" if getattr(business, "tcs_connected", False) else
            "leopards" if getattr(business, "leopards_connected", False) else
            None
        )

        if courier == "shiprocket" and getattr(business, "shiprocket_connected", False):
            return {"courier": "shiprocket", "raw": ship_mcp.sr_track_awb(tracking_number)}
        if courier == "tcs" and getattr(business, "tcs_connected", False):
            return {"courier": "tcs", "raw": ship_mcp.tcs_track(tracking_number)}
        if courier == "leopards" and getattr(business, "leopards_connected", False):
            return {"courier": "leopards", "raw": ship_mcp.leo_track(tracking_number)}

        return {"error": f"No connected courier for this business (requested: {courier or 'none'})"}

    def answer_where_is_my_order(self, business, tracking_number: str, courier: str = None) -> dict:
        tracking = self._track(business, tracking_number, courier)
        if tracking.get("error"):
            return tracking

        prompt = f"""
A customer is asking where their order is. Here is the raw tracking
data from {tracking['courier']}:
{tracking['raw']}

Write a short, reassuring 2-3 sentence reply with the current status
and, if available, the expected delivery window. If the data shows a
delay or exception, acknowledge it plainly and say what happens next.
Do not invent a date that isn't in the data.
"""
        reply_text = generate_response(prompt).strip()
        return {"tracking": tracking, "reply": reply_text}
