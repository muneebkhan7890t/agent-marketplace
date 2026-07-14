"""
agents/abandoned_cart_agent.py
----------------------------------
Abandoned Cart Recovery Agent -- Shopify (for the checkout data) +
Mailchimp/SendGrid (to actually send the nudge). Finds checkouts that
were started but never completed and sends a short recovery email.

Paste -> backend/app/agents/abandoned_cart_agent.py
"""

from app.mcp import shopify as shopify_mcp
from app.mcp import mailchimp as mailchimp_mcp
from app.ai.huggingface_client import generate_response
from app.integrations.sendgrid.service import SendGridService


class AbandonedCartAgent:

    role_prompt = "You write short, warm, non-pushy abandoned-cart recovery emails."

    def find_abandoned_checkouts(self, business, limit: int = 20) -> list:
        if not getattr(business, "shopify_connected", False):
            return []
        return shopify_mcp.get_abandoned_checkouts(business.id, limit=limit)

    def _draft_recovery_copy(self, checkout: dict, business_name: str) -> dict:
        items = checkout.get("line_items", [])
        item_names = [i.get("title", "an item") for i in items] or ["your cart"]
        prompt = f"""
Write a short cart-recovery email for {business_name}. The customer
added {item_names} to their cart but didn't finish checking out.

Return two parts, separated by a line "---":
1. A subject line (under 8 words)
2. A 3-4 sentence email body. Friendly, no pressure, one soft call to
action to complete checkout. Do not invent a discount code unless
told to.
"""
        raw = generate_response(prompt).strip()
        if "---" in raw:
            subject, body = raw.split("---", 1)
        else:
            subject, body = "You left something in your cart", raw
        return {"subject": subject.strip(), "body": body.strip()}

    def recover_cart(self, business, checkout: dict) -> dict:
        """
        Sends one recovery email for one abandoned checkout. Also
        upserts the shopper into Mailchimp so they land in any broader
        "abandoned cart" automation/segment the merchant has set up.
        """
        email = checkout.get("email")
        if not email:
            return {"skipped": True, "reason": "checkout has no email on file"}

        copy = self._draft_recovery_copy(checkout, business.business_name)

        mailchimp_result = None
        if getattr(business, "mailchimp_connected", False) and getattr(business, "mailchimp_list_id", None):
            try:
                mailchimp_result = mailchimp_mcp.subscribe(
                    list_id=business.mailchimp_list_id,
                    email=email,
                    tags=["abandoned_cart"],
                )
            except Exception as exc:
                mailchimp_result = {"error": str(exc)}

        send_result = SendGridService().send(
            to_email=email,
            subject=copy["subject"],
            html_content=f"<p>{copy['body']}</p>",
        )

        return {
            "checkout_id": checkout.get("id"),
            "email": email,
            "subject": copy["subject"],
            "body": copy["body"],
            "email_send_result": send_result,
            "mailchimp_result": mailchimp_result,
        }

    def run_recovery_sweep(self, business, limit: int = 20) -> dict:
        checkouts = self.find_abandoned_checkouts(business, limit=limit)
        results = [self.recover_cart(business, c) for c in checkouts]
        return {"checkouts_found": len(checkouts), "results": results}
