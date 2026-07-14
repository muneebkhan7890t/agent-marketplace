"""
mcp/stripe.py
Paste → backend/app/mcp/stripe.py  (replaces existing empty file)
"""
from app.integrations.stripe.service import StripeService

_svc = None
def _s() -> StripeService:
    global _svc
    if not _svc: _svc = StripeService()
    return _svc

def create_payment_intent(amount_cents: int, currency: str = "usd", customer_id: str = None, metadata: dict = None) -> dict:
    return _s().create_payment_intent(amount_cents, currency, customer_id, metadata)

def get_failed_payments(limit: int = 20) -> list:  return _s().get_failed_payments(limit)
def find_recent_succeeded_payment_by_email(email: str) -> dict:
    return _s().find_recent_succeeded_payment_by_email(email)
def create_refund(payment_intent_id: str, amount_cents: int = None) -> dict:
    return _s().create_refund(payment_intent_id, amount_cents)
def get_balance() -> dict:                          return _s().get_balance()
def list_customers(limit: int = 20) -> list:        return _s().list_customers(limit)
def create_customer(email: str, name: str = "") -> dict: return _s().create_customer(email, name)
def verify_webhook(payload: bytes, sig: str) -> dict: return StripeService.verify_webhook(payload, sig)