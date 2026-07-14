"""
mcp/amazon.py
-------------
MCP abstraction layer for Amazon SP-API.
"""

from app.integrations.amazon.service import AmazonSellerService
from app.integrations.amazon.utils import parse_order, parse_inventory_summary

_service = None


def _get_service() -> AmazonSellerService:
    global _service
    if _service is None:
        _service = AmazonSellerService()
    return _service


# ------------------------------------------------------------------ #
# Orders
# ------------------------------------------------------------------ #

def get_orders(
    created_after: str = None,
    statuses: list = None,
    max_results: int = 20,
) -> list[dict]:
    service = _get_service()
    orders = service.get_orders(
        created_after=created_after,
        order_statuses=statuses,
        max_results=max_results,
    )
    return [parse_order(o) for o in orders]


def get_order(order_id: str) -> dict:
    service = _get_service()
    return parse_order(service.get_order(order_id))


def get_order_items(order_id: str) -> list:
    return _get_service().get_order_items(order_id)


# ------------------------------------------------------------------ #
# Inventory
# ------------------------------------------------------------------ #

def get_inventory(skus: list = None) -> list[dict]:
    service = _get_service()
    summaries = service.get_inventory_summary(skus=skus)
    return [parse_inventory_summary(s) for s in summaries]


def get_low_inventory(threshold: int = 5) -> list[dict]:
    service = _get_service()
    return [parse_inventory_summary(s) for s in service.get_low_inventory(threshold)]


# ------------------------------------------------------------------ #
# Catalog
# ------------------------------------------------------------------ #

def search_catalog(keywords: str) -> list:
    return _get_service().search_catalog(keywords)


# ------------------------------------------------------------------ #
# Reports
# ------------------------------------------------------------------ #

def request_report(report_type: str) -> str:
    return _get_service().request_report(report_type)


def get_report_status(report_id: str) -> dict:
    return _get_service().get_report_status(report_id)