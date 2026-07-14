class ShopifyConnector:

    def get_orders(self):

        return {
            "status": "success",
            "orders": []
        }

    def get_products(self):

        return {
            "status": "success",
            "products": []
        }
    
"""
mcp/shopify.py
--------------
MCP abstraction layer for Shopify.
Agents import from here — never from integrations/shopify directly.
Handles credential loading from the Business row.
"""

from app.database import SessionLocal
from app.models.business import Business
from app.integrations.shopify.service import ShopifyService
from app.integrations.shopify.utils import parse_order, parse_product, is_low_stock


def _get_service(business_id: int) -> ShopifyService:
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            raise ValueError(f"Business {business_id} not found")
        if not business.shopify_connected:
            raise ValueError(f"Shopify not connected for business {business_id}")
        return ShopifyService(
            shop=business.shopify_store_url,
            access_token=business.shopify_access_token,
        )
    finally:
        db.close()


# ------------------------------------------------------------------ #
# Orders
# ------------------------------------------------------------------ #

def get_orders(business_id: int, status: str = "any", limit: int = 20) -> list[dict]:
    service = _get_service(business_id)
    orders = service.get_orders(status=status, limit=limit)
    return [parse_order(o) for o in orders]


def get_order(business_id: int, order_id: int) -> dict:
    service = _get_service(business_id)
    return parse_order(service.get_order(order_id))


def cancel_order(business_id: int, order_id: int, reason: str = "customer") -> dict:
    service = _get_service(business_id)
    return service.cancel_order(order_id, reason)


def add_order_note(business_id: int, order_id: int, note: str) -> dict:
    service = _get_service(business_id)
    return service.update_order_note(order_id, note)


# ------------------------------------------------------------------ #
# Products & Inventory
# ------------------------------------------------------------------ #

def get_products(business_id: int, limit: int = 20) -> list[dict]:
    service = _get_service(business_id)
    products = service.get_products(limit=limit)
    return [parse_product(p) for p in products]


def get_low_stock_products(business_id: int, threshold: int = 5) -> list[dict]:
    service = _get_service(business_id)
    products = service.get_products(limit=100)
    return [parse_product(p) for p in products if is_low_stock(p, threshold)]


def update_inventory(
    business_id: int,
    inventory_item_id: int,
    location_id: int,
    quantity: int,
) -> dict:
    service = _get_service(business_id)
    return service.set_inventory_level(inventory_item_id, location_id, quantity)


# ------------------------------------------------------------------ #
# Customers
# ------------------------------------------------------------------ #

def get_customers(business_id: int, limit: int = 20) -> list:
    service = _get_service(business_id)
    return service.get_customers(limit=limit)


def search_customers(business_id: int, query: str) -> list:
    service = _get_service(business_id)
    return service.search_customers(query)


# ------------------------------------------------------------------ #
# Abandoned checkouts
# ------------------------------------------------------------------ #

def get_abandoned_checkouts(business_id: int, limit: int = 20) -> list[dict]:
    service = _get_service(business_id)
    return service.get_abandoned_checkouts(limit=limit)


# ------------------------------------------------------------------ #
# Fulfillments
# ------------------------------------------------------------------ #

def create_fulfillment(
    business_id: int,
    order_id: int,
    tracking_number: str,
    tracking_company: str,
) -> dict:
    service = _get_service(business_id)
    return service.create_fulfillment(order_id, tracking_number, tracking_company)