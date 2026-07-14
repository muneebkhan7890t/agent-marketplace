"""
mcp/woocommerce.py
------------------
MCP abstraction layer for WooCommerce.
"""

from app.database import SessionLocal
from app.models.business import Business
from app.integrations.woocommerce.service import WooCommerceService
from app.integrations.woocommerce.utils import parse_order, parse_product


def _get_service(business_id: int) -> WooCommerceService:
    db = SessionLocal()
    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            raise ValueError(f"Business {business_id} not found")
        if not business.woo_connected:
            raise ValueError(f"WooCommerce not connected for business {business_id}")
        return WooCommerceService(
            store_url=business.woo_store_url,
            consumer_key=business.woo_consumer_key,
            consumer_secret=business.woo_consumer_secret,
        )
    finally:
        db.close()


# ------------------------------------------------------------------ #
# Orders
# ------------------------------------------------------------------ #

def get_orders(business_id: int, status: str = "any", per_page: int = 20) -> list[dict]:
    service = _get_service(business_id)
    return [parse_order(o) for o in service.get_orders(status=status, per_page=per_page)]


def get_order(business_id: int, order_id: int) -> dict:
    service = _get_service(business_id)
    return parse_order(service.get_order(order_id))


def update_order_status(business_id: int, order_id: int, status: str) -> dict:
    service = _get_service(business_id)
    return service.update_order_status(order_id, status)


def add_order_note(business_id: int, order_id: int, note: str, customer_note: bool = False) -> dict:
    service = _get_service(business_id)
    return service.add_order_note(order_id, note, customer_note)


def create_refund(business_id: int, order_id: int, amount: str, reason: str = "") -> dict:
    service = _get_service(business_id)
    return service.create_refund(order_id, amount, reason)


# ------------------------------------------------------------------ #
# Products & Inventory
# ------------------------------------------------------------------ #

def get_products(business_id: int, per_page: int = 20) -> list[dict]:
    service = _get_service(business_id)
    return [parse_product(p) for p in service.get_products(per_page=per_page)]


def get_low_stock_products(business_id: int, threshold: int = 5) -> list[dict]:
    service = _get_service(business_id)
    return [parse_product(p) for p in service.get_low_stock_products(threshold=threshold)]


def update_stock(business_id: int, product_id: int, quantity: int) -> dict:
    service = _get_service(business_id)
    return service.update_stock(product_id, quantity)


# ------------------------------------------------------------------ #
# Customers
# ------------------------------------------------------------------ #

def get_customers(business_id: int, per_page: int = 20) -> list:
    service = _get_service(business_id)
    return service.get_customers(per_page=per_page)


def search_customers(business_id: int, search: str) -> list:
    service = _get_service(business_id)
    return service.search_customers(search)


# ------------------------------------------------------------------ #
# Reports
# ------------------------------------------------------------------ #

def get_sales_report(business_id: int, period: str = "week") -> dict:
    service = _get_service(business_id)
    return service.get_sales_report(period=period)