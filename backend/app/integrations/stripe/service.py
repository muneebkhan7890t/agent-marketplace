"""
integrations/stripe/service.py
-------------------------------
Stripe payments integration.
Paste → backend/app/integrations/stripe/service.py

Required env vars:
  STRIPE_SECRET_KEY       ← sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET   ← whsec_... from Stripe dashboard
"""

import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


class StripeService:

    # ── Customers ─────────────────────────────────────────────────────

    def create_customer(self, email: str, name: str = "", metadata: dict = None) -> dict:
        return stripe.Customer.create(email=email, name=name, metadata=metadata or {})

    def get_customer(self, customer_id: str) -> dict:
        return stripe.Customer.retrieve(customer_id)

    def list_customers(self, limit: int = 20) -> list:
        return stripe.Customer.list(limit=limit).data

    # ── Payments / Payment Intents ────────────────────────────────────

    def create_payment_intent(self, amount_cents: int, currency: str = "usd", customer_id: str = None, metadata: dict = None) -> dict:
        """amount_cents: e.g. 4999 = $49.99"""
        kwargs = {
            "amount":   amount_cents,
            "currency": currency,
            "metadata": metadata or {},
            "automatic_payment_methods": {"enabled": True},
        }
        if customer_id:
            kwargs["customer"] = customer_id
        return stripe.PaymentIntent.create(**kwargs)

    def get_payment_intent(self, pi_id: str) -> dict:
        return stripe.PaymentIntent.retrieve(pi_id)

    def list_payment_intents(self, limit: int = 20, customer_id: str = None) -> list:
        kwargs = {"limit": limit}
        if customer_id:
            kwargs["customer"] = customer_id
        return stripe.PaymentIntent.list(**kwargs).data

    # ── Subscriptions ─────────────────────────────────────────────────

    def create_subscription(self, customer_id: str, price_id: str) -> dict:
        return stripe.Subscription.create(customer=customer_id, items=[{"price": price_id}])

    def cancel_subscription(self, subscription_id: str) -> dict:
        return stripe.Subscription.delete(subscription_id)

    def list_subscriptions(self, customer_id: str) -> list:
        return stripe.Subscription.list(customer=customer_id).data

    # ── Refunds ───────────────────────────────────────────────────────

    def create_refund(self, payment_intent_id: str, amount_cents: int = None, reason: str = "requested_by_customer") -> dict:
        kwargs = {"payment_intent": payment_intent_id, "reason": reason}
        if amount_cents:
            kwargs["amount"] = amount_cents
        return stripe.Refund.create(**kwargs)

    # ── Failed payments ───────────────────────────────────────────────

    def get_failed_payments(self, limit: int = 20) -> list:
        """Return recent payment intents that failed."""
        all_pis = stripe.PaymentIntent.list(limit=limit).data
        return [pi for pi in all_pis if pi.get("status") == "requires_payment_method"]

    # ── Lookup helpers for AI-proposed actions ──────────────────────────

    def find_recent_succeeded_payment_by_email(self, email: str, limit: int = 20) -> dict:
        """
        Best-effort lookup used when the AI proposes a refund: find the
        Stripe customer matching this email, then their most recent
        successful payment. Returns {} if nothing is found -- the human
        reviewer can still fill in a payment_intent_id manually.
        """
        customers = stripe.Customer.list(email=email, limit=5).data
        if not customers:
            return {}

        for customer in customers:
            pis = stripe.PaymentIntent.list(customer=customer["id"], limit=limit).data
            succeeded = [pi for pi in pis if pi.get("status") == "succeeded"]
            if succeeded:
                latest = succeeded[0]
                return {
                    "customer_id": customer["id"],
                    "payment_intent_id": latest["id"],
                    "amount_cents": latest["amount"],
                    "currency": latest["currency"],
                    "created": latest["created"],
                }
        return {}

    # ── Webhook verification ──────────────────────────────────────────

    @staticmethod
    def verify_webhook(payload: bytes, sig_header: str) -> dict:
        """Raises stripe.error.SignatureVerificationError if invalid."""
        return stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)

    # ── Revenue summary ───────────────────────────────────────────────

    def get_balance(self) -> dict:
        bal = stripe.Balance.retrieve()
        return {
            "available": bal["available"],
            "pending":   bal["pending"],
        }