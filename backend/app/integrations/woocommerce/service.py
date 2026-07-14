"""
integrations/woocommerce/service.py
------------------------------------
Low-level wrapper around the WooCommerce REST API v3.
Uses HTTP Basic Auth with consumer key + secret.
"""

import requests
from requests.auth import HTTPBasicAuth


class WooCommerceService:

    def __init__(self, store_url: str, consumer_key: str, consumer_secret: str):
        self.base_url = f"{store_url.rstrip('/')}/wp-json/wc/v3"
        self.auth     = HTTPBasicAuth(consumer_key, consumer_secret)
        self.headers  = {"Content-Type": "application/json"}

    def _get(self, endpoint: str, params: dict = None) -> any:
        r = requests.get(
            f"{self.base_url}{endpoint}",
            auth=self.headers,
            params=params or {},
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        r = requests.post(
            f"{self.base_url}{endpoint}",
            auth=self.auth,
            json=data,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    def _put(self, endpoint: str, data: dict) -> dict:
        r = requests.put(
            f"{self.base_url}{endpoint}",
            auth=self.auth,
            json=data,
            headers=self.headers,
        )
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ #
    # Orders
    # ------------------------------------------------------------------ #

    def get_orders(self, status: str = "any", per_page: int = 20) -> list:
        return self._get("/orders", {"status": status, "per_page": per_page})

    def get_order(self, order_id: int) -> dict:
        return self._get(f"/orders/{order_id}")

    def update_order_status(self, order_id: int, status: str) -> dict:
        """status: pending | processing | on-hold | completed | cancelled | refunded"""
        return self._put(f"/orders/{order_id}", {"status": status})

    def add_order_note(self, order_id: int, note: str, customer_note: bool = False) -> dict:
        return self._post(
            f"/orders/{order_id}/notes",
            {"note": note, "customer_note": customer_note},
        )

    def create_refund(self, order_id: int, amount: str, reason: str = "") -> dict:
        return self._post(
            f"/orders/{order_id}/refunds",
            {"amount": amount, "reason": reason},
        )

    # ------------------------------------------------------------------ #
    # Products
    # ------------------------------------------------------------------ #

    def get_products(self, per_page: int = 20, stock_status: str = None) -> list:
        params = {"per_page": per_page}
        if stock_status:
            params["stock_status"] = stock_status   # instock | outofstock | onbackorder
        return self._get("/products", params)

    def get_product(self, product_id: int) -> dict:
        return self._get(f"/products/{product_id}")

    def update_stock(self, product_id: int, quantity: int) -> dict:
        return self._put(
            f"/products/{product_id}",
            {"stock_quantity": quantity, "manage_stock": True},
        )

    def get_low_stock_products(self, threshold: int = 5) -> list:
        products = self.get_products(per_page=100)
        return [
            p for p in products
            if p.get("manage_stock") and (p.get("stock_quantity") or 0) <= threshold
        ]

    # ------------------------------------------------------------------ #
    # Customers
    # ------------------------------------------------------------------ #

    def get_customers(self, per_page: int = 20) -> list:
        return self._get("/customers", {"per_page": per_page})

    def get_customer(self, customer_id: int) -> dict:
        return self._get(f"/customers/{customer_id}")

    def search_customers(self, search: str) -> list:
        return self._get("/customers", {"search": search})

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #

    def get_sales_report(self, period: str = "week") -> dict:
        """period: week | month | last_month | year"""
        return self._get("/reports/sales", {"period": period})

    def get_top_sellers(self, period: str = "week") -> list:
        return self._get("/reports/top_sellers", {"period": period})