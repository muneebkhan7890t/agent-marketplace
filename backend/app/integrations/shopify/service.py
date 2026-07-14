"""
integrations/shopify/service.py
--------------------------------
Low-level wrapper around the Shopify REST Admin API.
Accepts a shop domain + access token.
"""

import requests
from typing import Optional


class ShopifyService:

    def __init__(self, shop: str, access_token: str):
        self.shop         = shop
        self.access_token = access_token
        self.base_url     = f"https://{shop}/admin/api/2024-01"
        self.headers      = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        r = requests.get(url, headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        r = requests.post(url, headers=self.headers, json=data)
        r.raise_for_status()
        return r.json()

    def _put(self, endpoint: str, data: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        r = requests.put(url, headers=self.headers, json=data)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ #
    # Orders
    # ------------------------------------------------------------------ #

    def get_orders(self, status: str = "any", limit: int = 20) -> list:
        data = self._get("/orders.json", {"status": status, "limit": limit})
        return data.get("orders", [])

    def get_order(self, order_id: int) -> dict:
        data = self._get(f"/orders/{order_id}.json")
        return data.get("order", {})

    def cancel_order(self, order_id: int, reason: str = "customer") -> dict:
        data = self._post(f"/orders/{order_id}/cancel.json", {"reason": reason})
        return data.get("order", {})

    def close_order(self, order_id: int) -> dict:
        data = self._post(f"/orders/{order_id}/close.json", {})
        return data.get("order", {})

    def update_order_note(self, order_id: int, note: str) -> dict:
        data = self._put(f"/orders/{order_id}.json", {"order": {"id": order_id, "note": note}})
        return data.get("order", {})

    # ------------------------------------------------------------------ #
    # Products
    # ------------------------------------------------------------------ #

    def get_products(self, limit: int = 20) -> list:
        data = self._get("/products.json", {"limit": limit})
        return data.get("products", [])

    def get_product(self, product_id: int) -> dict:
        data = self._get(f"/products/{product_id}.json")
        return data.get("product", {})

    def update_product(self, product_id: int, fields: dict) -> dict:
        data = self._put(
            f"/products/{product_id}.json",
            {"product": {"id": product_id, **fields}},
        )
        return data.get("product", {})

    # ------------------------------------------------------------------ #
    # Inventory
    # ------------------------------------------------------------------ #

    def get_inventory_levels(self, location_id: Optional[int] = None) -> list:
        params = {}
        if location_id:
            params["location_ids"] = location_id
        data = self._get("/inventory_levels.json", params)
        return data.get("inventory_levels", [])

    def set_inventory_level(
        self, inventory_item_id: int, location_id: int, available: int
    ) -> dict:
        return self._post(
            "/inventory_levels/set.json",
            {
                "location_id":        location_id,
                "inventory_item_id":  inventory_item_id,
                "available":          available,
            },
        )

    # ------------------------------------------------------------------ #
    # Customers
    # ------------------------------------------------------------------ #

    def get_customers(self, limit: int = 20) -> list:
        data = self._get("/customers.json", {"limit": limit})
        return data.get("customers", [])

    def get_customer(self, customer_id: int) -> dict:
        data = self._get(f"/customers/{customer_id}.json")
        return data.get("customer", {})

    def search_customers(self, query: str) -> list:
        data = self._get("/customers/search.json", {"query": query})
        return data.get("customers", [])

    # ------------------------------------------------------------------ #
    # Fulfillments
    # ------------------------------------------------------------------ #

    def get_fulfillments(self, order_id: int) -> list:
        data = self._get(f"/orders/{order_id}/fulfillments.json")
        return data.get("fulfillments", [])

    def create_fulfillment(self, order_id: int, tracking_number: str, tracking_company: str) -> dict:
        data = self._post(
            f"/orders/{order_id}/fulfillments.json",
            {
                "fulfillment": {
                    "tracking_number":  tracking_number,
                    "tracking_company": tracking_company,
                    "notify_customer":  True,
                }
            },
        )
        return data.get("fulfillment", {})

    # ------------------------------------------------------------------ #
    # Abandoned checkouts
    # ------------------------------------------------------------------ #

    def get_abandoned_checkouts(self, limit: int = 20) -> list:
        data = self._get("/checkouts.json", {"limit": limit, "status": "open"})
        return data.get("checkouts", [])

    # ------------------------------------------------------------------ #
    # Shop info
    # ------------------------------------------------------------------ #

    def get_shop_info(self) -> dict:
        data = self._get("/shop.json")
        return data.get("shop", {})