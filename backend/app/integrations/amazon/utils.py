"""
integrations/amazon/utils.py
-----------------------------
Helpers for parsing Amazon SP-API payloads.
"""


def parse_order(order: dict) -> dict:
    return {
        "id":              order.get("AmazonOrderId"),
        "status":          order.get("OrderStatus"),
        "total":           order.get("OrderTotal", {}).get("Amount"),
        "currency":        order.get("OrderTotal", {}).get("CurrencyCode"),
        "channel":         order.get("SalesChannel"),
        "fulfillment":     order.get("FulfillmentChannel"),  # AFN=FBA, MFN=seller
        "buyer_email":     order.get("BuyerInfo", {}).get("BuyerEmail", ""),
        "buyer_name":      order.get("BuyerInfo", {}).get("BuyerName", ""),
        "items_shipped":   order.get("NumberOfItemsShipped", 0),
        "items_unshipped": order.get("NumberOfItemsUnshipped", 0),
        "purchase_date":   order.get("PurchaseDate"),
        "ship_by":         order.get("LatestShipDate"),
    }


def parse_inventory_summary(summary: dict) -> dict:
    details = summary.get("inventoryDetails", {})
    return {
        "sku":             summary.get("sellerSku"),
        "asin":            summary.get("asin"),
        "fnsku":           summary.get("fnSku"),
        "condition":       summary.get("condition"),
        "fulfillable":     details.get("fulfillableQuantity", 0),
        "inbound":         details.get("inboundWorkingQuantity", 0),
        "reserved":        details.get("reservedQuantity", {}).get("totalReservedQuantity", 0),
        "unfulfillable":   details.get("unfulfillableQuantity", {}).get("totalUnfulfillableQuantity", 0),
    }


def format_order_summary(order: dict) -> str:
    p = parse_order(order)
    return (
        f"Amazon Order {p['id']} | Status: {p['status']} | "
        f"{p['currency']} {p['total']} | Fulfillment: {p['fulfillment']}"
    )