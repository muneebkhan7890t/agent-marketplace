"""
mcp/shiprocket.py
Paste → backend/app/mcp/shiprocket.py
"""
from app.integrations.shiprocket.service import ShiprocketService, TCSService, LeopardsService

_sr = None; _tcs = None; _lp = None
def _s(): global _sr; _sr = _sr or ShiprocketService(); return _sr
def _t(): global _tcs; _tcs = _tcs or TCSService(); return _tcs
def _l(): global _lp; _lp = _lp or LeopardsService(); return _lp

# Shiprocket
def sr_create_order(data: dict) -> dict:              return _s().create_order(data)
def sr_track(shipment_id: str) -> dict:               return _s().track_shipment(shipment_id)
def sr_track_awb(awb: str) -> dict:                   return _s().track_by_awb(awb)
def sr_cancel(order_ids: list) -> dict:               return _s().cancel_order(order_ids)
def sr_get_shipments(status: str = None) -> dict:     return _s().get_shipments(status)

# TCS
def tcs_book(sender_name, sender_phone, sender_city, receiver_name, receiver_phone, receiver_city, receiver_address, weight, cod=0) -> dict:
    return _t().book_shipment(sender_name, sender_phone, sender_city, receiver_name, receiver_phone, receiver_city, receiver_address, weight, cod_amount=cod)
def tcs_track(tracking_no: str) -> dict:              return _t().track(tracking_no)
def tcs_cities() -> list:                             return _t().get_cities()

# Leopards
def leo_book(**kwargs) -> dict:                       return _l().book_packet(**kwargs)
def leo_track(tracking_no: str) -> dict:              return _l().track_packet(tracking_no)
def leo_cities() -> list:                             return _l().get_cities()