"""
agents/reporting_agent.py
------------------------------
Reporting Agent -- pushes a daily/weekly summary into Google Sheets.
The Sheets integration (export_orders, export_weekly_summary) already
existed; this is what actually calls it on a schedule and assembles
the numbers from Shopify/WooCommerce first.

Paste -> backend/app/agents/reporting_agent.py
"""

from app.mcp import shopify as shopify_mcp
from app.mcp import woocommerce as woo_mcp
from app.mcp import google_sheets as sheets_mcp


class ReportingAgent:

    def _active_store(self, business):
        if getattr(business, "shopify_connected", False):
            return "shopify"
        if getattr(business, "woo_connected", False):
            return "woocommerce"
        return None

    def _fetch_recent_orders(self, business, limit: int = 100) -> list:
        store = self._active_store(business)
        if store == "shopify":
            return shopify_mcp.get_orders(business.id, status="any", limit=limit)
        if store == "woocommerce":
            return woo_mcp.get_orders(business.id, status="any", per_page=limit)
        return []

    def _summarize(self, orders: list) -> dict:
        total_revenue = 0.0
        for o in orders:
            try:
                total_revenue += float(o.get("total_price") or o.get("total") or 0)
            except (TypeError, ValueError):
                pass
        return {
            "order_count": len(orders),
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(total_revenue / len(orders), 2) if orders else 0,
        }

    def send_summary_to_sheets(self, business) -> dict:
        if not getattr(business, "sheets_connected", False) or not getattr(business, "sheets_spreadsheet_id", None):
            return {"error": "Google Sheets not connected for this business"}

        orders = self._fetch_recent_orders(business)
        summary = self._summarize(orders)

        export_result = {}
        try:
            export_result["orders_export"] = sheets_mcp.export_orders(
                business.sheets_spreadsheet_id, orders
            )
        except Exception as exc:
            export_result["orders_export_error"] = str(exc)

        try:
            export_result["summary_export"] = sheets_mcp.export_weekly_summary(
                business.sheets_spreadsheet_id, summary
            )
        except Exception as exc:
            export_result["summary_export_error"] = str(exc)

        return {"summary": summary, "export_result": export_result}
