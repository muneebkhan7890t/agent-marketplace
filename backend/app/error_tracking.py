"""
error_tracking.py
------------------
Sentry integration. Missing piece: previously, if an agent run failed at
3am (a bad Gemini response, a dead Shopify token, a Celery task that
raised), the only record was a `print()` that scrolled off whatever
terminal happened to be open. Nobody found out until a customer complained.

Paste -> backend/app/error_tracking.py
Wired in main.py:
    from app.error_tracking import init_sentry
    init_sentry()   # call this first, before creating the FastAPI app

Env vars:
  SENTRY_DSN          <- from your Sentry project settings
  SENTRY_ENVIRONMENT  <- optional, defaults to "development"

If sentry-sdk isn't installed or SENTRY_DSN isn't set, everything in this
module becomes a no-op that falls back to print() -- so the app still runs
fine without Sentry configured, it just won't have remote visibility.
"""

import os
import traceback

_sentry_enabled = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    _SENTRY_SDK_AVAILABLE = True
except ImportError:
    _SENTRY_SDK_AVAILABLE = False


def init_sentry():
    global _sentry_enabled

    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        print("[ErrorTracking] SENTRY_DSN not set -- error tracking disabled (falling back to console logging).")
        return

    if not _SENTRY_SDK_AVAILABLE:
        print("[ErrorTracking] SENTRY_DSN is set but sentry-sdk isn't installed. "
              "Run: pip install sentry-sdk[fastapi]")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
    )
    _sentry_enabled = True
    print("[ErrorTracking] Sentry initialized.")


def capture_exception(exc: Exception, context: dict = None):
    """
    Call this from any except block that would otherwise just print().
    Safe to call even if Sentry was never initialized -- falls back to a
    structured console log so nothing is silently swallowed either way.
    """
    if _sentry_enabled and _SENTRY_SDK_AVAILABLE:
        with sentry_sdk.push_scope() as scope:
            for key, value in (context or {}).items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exc)
    else:
        print(f"[ErrorTracking] Unreported exception: {exc}")
        if context:
            print(f"[ErrorTracking] Context: {context}")
        traceback.print_exc()


def capture_message(message: str, level: str = "info", context: dict = None):
    if _sentry_enabled and _SENTRY_SDK_AVAILABLE:
        with sentry_sdk.push_scope() as scope:
            for key, value in (context or {}).items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        print(f"[ErrorTracking:{level}] {message} {context or ''}")
