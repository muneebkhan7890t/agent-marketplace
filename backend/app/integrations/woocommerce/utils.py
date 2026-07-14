"""
integrations/woocommerce/utils.py
----------------------------------
Helpers for parsing WooCommerce API payloads.
"""


def parse_order(order: dict) -> dict:
    billing = order.get("billing", {})
    return {
        "id":             order.get("id"),
        "order_number":   order.get("number"),
        "status":         order.get("status"),
        "total":          order.get("total"),
        "currency":       order.get("currency"),
        "customer_name":  f"{billing.get('first_name','')} {billing.get('last_name','')}".strip(),
        "customer_email": billing.get("email", ""),
        "customer_phone": billing.get("phone", ""),
        "items": [
            {
                "name":     i.get("name"),
                "quantity": i.get("quantity"),
                "total":    i.get("total"),
                "sku":      i.get("sku"),
            }
            for i in order.get("line_items", [])
        ],
        "payment_method": order.get("payment_method_title"),
        "date_created":   order.get("date_created"),
        "note":           order.get("customer_note", ""),
    }


def parse_product(product: dict) -> dict:
    return {
        "id":             product.get("id"),
        "name":           product.get("name"),
        "status":         product.get("status"),
        "sku":            product.get("sku"),
        "price":          product.get("price"),
        "stock_quantity": product.get("stock_quantity"),
        "stock_status":   product.get("stock_status"),
        "manage_stock":   product.get("manage_stock"),
        "categories":     [c.get("name") for c in product.get("categories", [])],
    }


def format_order_summary(order: dict) -> str:
    p = parse_order(order)
    return (
        f"Order #{p['order_number']} | {p['customer_name']} | "
        f"{p['currency']} {p['total']} | Status: {p['status']}"
    )