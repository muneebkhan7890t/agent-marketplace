"""
integrations/shopify/auth.py
-----------------------------
Shopify OAuth2 installation flow for public apps.

Flow:
  1. GET /shopify/connect?shop=mystore.myshopify.com&business_id=1
     → redirects merchant to Shopify permission screen
  2. Shopify redirects to GET /shopify/callback?code=...&shop=...&state=...
     → exchange code for permanent access token
     → store token on Business row
"""

import os
import hmac
import hashlib
import base64
import secrets
import requests
from urllib.parse import urlencode


SHOPIFY_API_KEY    = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")

# Base URL Shopify can reach to deliver webhooks (must be public, e.g. your
# ngrok URL in dev or your real domain in prod) -- NOT the OAuth redirect URI.
SHOPIFY_WEBHOOK_BASE_URL = os.getenv("SHOPIFY_WEBHOOK_BASE_URL", "http://localhost:8000")
SHOPIFY_SCOPES     = ",".join([
    "read_orders",
    "write_orders",
    "read_products",
    "write_products",
    "read_inventory",
    "write_inventory",
    "read_customers",
    "write_customers",
    "read_fulfillments",
    "write_fulfillments",
])


def build_auth_url(shop: str, state: str, redirect_uri: str) -> str:
    """Return the Shopify OAuth consent URL for the given shop."""
    params = {
        "client_id":    SHOPIFY_API_KEY,
        "scope":        SHOPIFY_SCOPES,
        "redirect_uri": redirect_uri,
        "state":        state,
        "grant_options[]": "per-user",
    }
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"


def verify_hmac(params: dict) -> bool:
    """
    Validate the HMAC Shopify attaches to every callback.
    Returns True if the request is genuine.
    """
    hmac_from_shopify = params.pop("hmac", "")
    sorted_params = "&".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    digest = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        sorted_params.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, hmac_from_shopify)


def generate_state() -> str:
    return secrets.token_urlsafe(32)


# ------------------------------------------------------------------ #
# Webhooks -- these power the "A to Z automation" (order created,
# inventory changed) that trigger the automation pipeline in
# app/services/shopify_automation.py.
#
# NOTE: this HMAC check is DIFFERENT from verify_hmac() above.
# OAuth-callback HMAC signs sorted query params. Webhook HMAC signs the
# raw request body and is base64 (not hex). Shopify computes both the
# same way but they are not interchangeable -- using the wrong one will
# always fail verification.
# ------------------------------------------------------------------ #

def verify_webhook_hmac(raw_body: bytes, hmac_header: str) -> bool:
    """Validate the X-Shopify-Hmac-Sha256 header Shopify sends on every webhook."""
    if not hmac_header:
        return False
    digest = hmac.new(
        SHOPIFY_API_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, hmac_header)


def register_order_webhooks(shop: str, access_token: str) -> list[dict]:
    """
    Register the webhooks the automation pipeline needs, right after OAuth
    finishes. Safe to call more than once -- Shopify rejects exact
    duplicates (same topic + address) rather than creating a second copy.

    Returns a list of {topic, status, error?} for each registration attempt,
    so the caller can log/surface partial failures instead of silently
    losing a topic.
    """
    topics = ["orders/create", "orders/paid", "inventory_levels/update"]
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    results = []
    for topic in topics:
        address = f"{SHOPIFY_WEBHOOK_BASE_URL}/shopify/webhooks/{topic.replace('/', '-')}"
        try:
            r = requests.post(
                f"https://{shop}/admin/api/2024-01/webhooks.json",
                headers=headers,
                json={"webhook": {"topic": topic, "address": address, "format": "json"}},
                timeout=10,
            )
            if r.status_code in (200, 201):
                results.append({"topic": topic, "status": "registered"})
            elif r.status_code == 422:
                # Almost always "address for this topic has already been taken" -- fine.
                results.append({"topic": topic, "status": "already_registered"})
            else:
                results.append({"topic": topic, "status": "failed", "error": r.text[:300]})
        except requests.RequestException as exc:
            results.append({"topic": topic, "status": "failed", "error": str(exc)})
    return results