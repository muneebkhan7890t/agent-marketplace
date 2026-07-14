"""
integrations/woocommerce/auth.py
---------------------------------
WooCommerce uses REST API Key authentication (no OAuth redirect needed).
Keys are generated manually in WP Admin → WooCommerce → Settings → Advanced → REST API.

Store the consumer_key + consumer_secret on the Business row.
"""

import os


def get_woo_credentials(business) -> tuple[str, str, str]:
    """
    Extract WooCommerce credentials from a Business model instance.
    Returns (store_url, consumer_key, consumer_secret).
    """
    if not business.woo_store_url:
        raise ValueError("WooCommerce store URL not set for this business")
    if not business.woo_consumer_key or not business.woo_consumer_secret:
        raise ValueError("WooCommerce API keys not set for this business")

    return (
        business.woo_store_url.rstrip("/"),
        business.woo_consumer_key,
        business.woo_consumer_secret,
    )


def validate_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify a WooCommerce webhook (uses HMAC-SHA256 with the webhook secret).
    """
    import hmac, hashlib, base64
    secret = os.getenv("WOO_WEBHOOK_SECRET", "")
    digest = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).digest()
    computed = base64.b64encode(digest).decode()
    return hmac.compare_digest(computed, signature)