"""
integrations/amazon/auth.py
-----------------------------
Amazon Selling Partner API (SP-API) authentication.
Uses LWA (Login with Amazon) to get access tokens.

Required env vars:
  AMAZON_CLIENT_ID
  AMAZON_CLIENT_SECRET
  AMAZON_REFRESH_TOKEN   ← obtained once during seller onboarding
  AMAZON_MARKETPLACE_ID  ← e.g. ATVPDKIKX0DER for US
"""

import os
import requests
from datetime import datetime, timedelta

_token_cache = {"token": None, "expires_at": datetime.min}

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


def get_access_token() -> str:
    """
    Return a valid LWA access token, refreshing if expired.
    Cached in memory for the token lifetime (~1 hour).
    """
    global _token_cache

    if _token_cache["token"] and datetime.utcnow() < _token_cache["expires_at"]:
        return _token_cache["token"]

    response = requests.post(
        LWA_TOKEN_URL,
        data={
            "grant_type":    "refresh_token",
            "refresh_token": os.getenv("AMAZON_REFRESH_TOKEN"),
            "client_id":     os.getenv("AMAZON_CLIENT_ID"),
            "client_secret": os.getenv("AMAZON_CLIENT_SECRET"),
        },
    )
    response.raise_for_status()
    data = response.json()

    _token_cache["token"]      = data["access_token"]
    _token_cache["expires_at"] = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600) - 60)

    return _token_cache["token"]


def get_auth_headers() -> dict:
    return {
        "x-amz-access-token": get_access_token(),
        "Content-Type":       "application/json",
    }