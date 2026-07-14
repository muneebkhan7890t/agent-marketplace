"""
integrations/amazon/service.py
--------------------------------
Wrapper around Amazon SP-API endpoints.
Covers Orders, Catalog Items, Inventory, and Notifications.
"""

import os
import requests
from .auth import get_auth_headers

MARKETPLACE_ID = os.getenv("AMAZON_MARKETPLACE_ID", "ATVPDKIKX0DER")
SP_API_BASE    = "https://sellingpartnerapi-na.amazon.com"


class AmazonSellerService:

    def __init__(self):
        self.base = SP_API_BASE
        self.marketplace_id = MARKETPLACE_ID

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(
            f"{self.base}{path}",
            headers=get_auth_headers(),
            params=params or {},
        )
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(
            f"{self.base}{path}",
            headers=get_auth_headers(),
            json=data,
        )
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ #
    # Orders
    # ------------------------------------------------------------------ #

    def get_orders(
        self,
        created_after: str = None,
        order_statuses: list = None,
        max_results: int = 20,
    ) -> list:
        """
        created_after: ISO-8601 string e.g. "2024-01-01T00:00:00Z"
        order_statuses: ["Unshipped", "PartiallyShipped", "Shipped", "Canceled"]
        """
        params = {
            "MarketplaceIds": self.marketplace_id,
            "MaxResultsPerPage": max_results,
        }
        if created_after:
            params["CreatedAfter"] = created_after
        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)

        data = self._get("/orders/v0/orders", params)
        return data.get("payload", {}).get("Orders", [])

    def get_order(self, order_id: str) -> dict:
        data = self._get(f"/orders/v0/orders/{order_id}")
        return data.get("payload", {})

    def get_order_items(self, order_id: str) -> list:
        data = self._get(f"/orders/v0/orders/{order_id}/orderItems")
        return data.get("payload", {}).get("OrderItems", [])

    # ------------------------------------------------------------------ #
    # Catalog / Listings
    # ------------------------------------------------------------------ #

    def search_catalog(self, keywords: str) -> list:
        params = {
            "keywords":       keywords,
            "marketplaceIds": self.marketplace_id,
        }
        data = self._get("/catalog/2022-04-01/items", params)
        return data.get("items", [])

    def get_listing(self, seller_id: str, sku: str) -> dict:
        params = {"marketplaceIds": self.marketplace_id}
        data = self._get(f"/listings/2021-08-01/items/{seller_id}/{sku}", params)
        return data.get("payload", data)

    # ------------------------------------------------------------------ #
    # Inventory
    # ------------------------------------------------------------------ #

    def get_inventory_summary(self, skus: list = None) -> list:
        params = {
            "details":          True,
            "marketplaceIds":   self.marketplace_id,
            "granularityType":  "Marketplace",
            "granularityId":    self.marketplace_id,
        }
        if skus:
            params["sellerSkus"] = ",".join(skus)

        data = self._get("/fba/inventory/v1/summaries", params)
        return data.get("payload", {}).get("inventorySummaries", [])

    def get_low_inventory(self, threshold: int = 5) -> list:
        summaries = self.get_inventory_summary()
        return [
            s for s in summaries
            if (s.get("inventoryDetails", {}).get("fulfillableQuantity") or 0) <= threshold
        ]

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #

    def request_report(self, report_type: str) -> str:
        """
        Request an async report. Returns reportId.
        report_type e.g.: "GET_FLAT_FILE_OPEN_LISTINGS_DATA"
        """
        data = self._post(
            "/reports/2021-06-30/reports",
            {
                "reportType":    report_type,
                "marketplaceIds": [self.marketplace_id],
            },
        )
        return data.get("reportId", "")

    def get_report_status(self, report_id: str) -> dict:
        data = self._get(f"/reports/2021-06-30/reports/{report_id}")
        return data.get("payload", data)