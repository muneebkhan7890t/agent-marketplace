"""
integrations/shopify/utils.py
------------------------------
Helper functions for parsing Shopify payloads.
"""

from datetime import datetime


def parse_order(order: dict) -> dict:
    """Flatten a Shopify order into a clean dict for agents."""
    customer = order.get("customer") or {}
    return {
        "id":              order.get("id"),
        "order_number":    order.get("order_number"),
        "status":          order.get("financial_status"),
        "fulfillment":     order.get("fulfillment_status"),
        "total_price":     order.get("total_price"),
        "currency":        order.get("currency"),
        "customer_name":   f"{customer.get('first_name','')} {customer.get('last_name','')}".strip(),
        "customer_email":  customer.get("email", ""),
        "item_count":      sum(i.get("quantity", 0) for i in order.get("line_items", [])),
        "items":           [
            {
                "title":    i.get("title"),
                "quantity": i.get("quantity"),
                "price":    i.get("price"),
                "sku":      i.get("sku"),
            }
            for i in order.get("line_items", [])
        ],
        "created_at":      order.get("created_at"),
        "note":            order.get("note", ""),
        "tags":            order.get("tags", ""),
    }


def parse_product(product: dict) -> dict:
    return {
        "id":           product.get("id"),
        "title":        product.get("title"),
        "status":       product.get("status"),
        "vendor":       product.get("vendor"),
        "product_type": product.get("product_type"),
        "variants":     [
            {
                "id":                v.get("id"),
                "title":             v.get("title"),
                "sku":               v.get("sku"),
                "price":             v.get("price"),
                "inventory_qty":     v.get("inventory_quantity"),
                "inventory_item_id": v.get("inventory_item_id"),
            }
            for v in product.get("variants", [])
        ],
        "created_at":   product.get("created_at"),
    }


def is_low_stock(product: dict, threshold: int = 5) -> bool:
    """Return True if any variant is below the stock threshold."""
    for variant in product.get("variants", []):
        if (variant.get("inventory_quantity") or 0) <= threshold:
            return True
    return False


def format_order_summary(order: dict) -> str:
    """Human-readable one-liner for agent logs / notifications."""
    p = parse_order(order)
    return (
        f"Order #{p['order_number']} | {p['customer_name']} | "
        f"{p['currency']} {p['total_price']} | Status: {p['status']} | "
        f"Fulfillment: {p['fulfillment']}"
    )