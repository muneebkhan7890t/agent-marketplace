"""
mcp/whatsapp.py  (compat shim)
-------------------------------
All real WhatsApp logic now lives in app/whatsapp_suite.py (one file,
all 10 phases). This module just re-exports the pieces other files
still import, so nothing elsewhere in the codebase breaks.
"""

from app.whatsapp_suite import (
    _get_service,
    get_business_id_for_phone_number_id,
    extract_phone_number_id,
)
from app.integrations.whatsapp.service import WhatsAppService


def send_text(business_id: int, to: str, message: str) -> dict:
    return _get_service(business_id).send_text(to, message)


def send_template(business_id: int, to: str, name: str, lang: str = "en_US") -> dict:
    return _get_service(business_id).send_template(to, name, lang)


def send_order_update(business_id: int, to: str, order_id: str, status: str, tracking: str = "") -> dict:
    return _get_service(business_id).send_order_update(to, order_id, status, tracking)


def mark_as_read(business_id: int, message_id: str) -> dict:
    return _get_service(business_id).mark_as_read(message_id)


def parse_incoming(payload: dict) -> list:
    return WhatsAppService.parse_incoming(payload)


class WhatsAppConnector:
    """Legacy convenience wrapper kept for runtime/tool_executor.py.
    Every send is now scoped to a business, so pass business_id to the
    constructor: WhatsAppConnector(business_id=...)."""

    def __init__(self, business_id: int = None):
        self.business_id = business_id

    def send_message(self, to: str, message: str):
        if self.business_id is None:
            raise ValueError("WhatsAppConnector needs a business_id (WhatsAppConnector(business_id=...)) "
                              "-- WhatsApp sends are scoped per business now.")
        return send_text(self.business_id, to, message)
