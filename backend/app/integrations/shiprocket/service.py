"""
integrations/shiprocket/service.py
------------------------------------
Shiprocket (India) + TCS Courier (Pakistan) + Leopards Courier (Pakistan).
Paste → backend/app/integrations/shiprocket/service.py

Env vars:
  SHIPROCKET_EMAIL / SHIPROCKET_PASSWORD
  TCS_USERNAME / TCS_PASSWORD / TCS_COST_CENTER
  LEOPARDS_API_KEY / LEOPARDS_API_PASSWORD
"""

import os
import requests


# ══════════════════════════════════════════════════════════════════════
# SHIPROCKET (India)
# ══════════════════════════════════════════════════════════════════════

class ShiprocketService:

    BASE = "https://apiv2.shiprocket.in/v1/external"

    def __init__(self):
        self._token = None

    def _get_token(self) -> str:
        if self._token:
            return self._token
        r = requests.post(f"{self.BASE}/auth/login", json={
            "email":    os.getenv("SHIPROCKET_EMAIL", ""),
            "password": os.getenv("SHIPROCKET_PASSWORD", ""),
        })
        r.raise_for_status()
        self._token = r.json()["token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}", "Content-Type": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{self.BASE}{path}", headers=self._headers(), params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{self.BASE}{path}", headers=self._headers(), json=data)
        r.raise_for_status()
        return r.json()

    def create_order(self, order_data: dict) -> dict:
        """
        order_data keys: order_id, order_date, pickup_location, channel_id,
        billing_customer_name, billing_address, billing_city, billing_pincode,
        billing_state, billing_country, billing_email, billing_phone,
        shipping_is_billing, order_items (list), payment_method, sub_total, length, breadth, height, weight
        """
        return self._post("/orders/create/adhoc", order_data)

    def get_order(self, order_id: str) -> dict:
        return self._get(f"/orders/show/{order_id}")

    def track_shipment(self, shipment_id: str) -> dict:
        return self._get(f"/courier/track/shipment/{shipment_id}")

    def track_by_awb(self, awb: str) -> dict:
        return self._get(f"/courier/track/awbs/{awb}")

    def get_courier_serviceability(self, pickup_pin: str, delivery_pin: str, weight: float, cod: int = 0) -> dict:
        return self._get("/courier/serviceability/", {
            "pickup_postcode":   pickup_pin,
            "delivery_postcode": delivery_pin,
            "weight":            weight,
            "cod":               cod,
        })

    def cancel_order(self, order_ids: list) -> dict:
        return self._post("/orders/cancel", {"ids": order_ids})

    def get_shipments(self, status: str = None) -> dict:
        params = {}
        if status:
            params["status"] = status
        return self._get("/shipments", params)


# ══════════════════════════════════════════════════════════════════════
# TCS COURIER (Pakistan)
# ══════════════════════════════════════════════════════════════════════

class TCSService:
    """
    TCS eXpress Courier Pakistan — uses TCS Ship API.
    Docs: https://ship.tcs.com.pk/api
    """

    BASE = "https://ship.tcs.com.pk/api"

    def __init__(self):
        self.username    = os.getenv("TCS_USERNAME", "")
        self.password    = os.getenv("TCS_PASSWORD", "")
        self.cost_center = os.getenv("TCS_COST_CENTER", "")

    def _auth(self) -> dict:
        return {"username": self.username, "password": self.password}

    def book_shipment(
        self,
        sender_name: str,
        sender_phone: str,
        sender_city: str,
        receiver_name: str,
        receiver_phone: str,
        receiver_city: str,
        receiver_address: str,
        weight_kg: float,
        pieces: int = 1,
        cod_amount: float = 0,
        description: str = "Ecommerce parcel",
    ) -> dict:
        data = {
            **self._auth(),
            "cost_center":      self.cost_center,
            "service_type_id":  "O",        # overnight
            "sender_name":      sender_name,
            "sender_phone":     sender_phone,
            "sender_city":      sender_city,
            "receiver_name":    receiver_name,
            "receiver_phone":   receiver_phone,
            "receiver_city":    receiver_city,
            "receiver_address": receiver_address,
            "weight":           weight_kg,
            "pieces":           pieces,
            "cod_amount":       cod_amount,
            "commodity_desc":   description,
        }
        r = requests.post(f"{self.BASE}/BookShipment", json=data)
        r.raise_for_status()
        return r.json()

    def track(self, tracking_number: str) -> dict:
        r = requests.post(f"{self.BASE}/Tracking", json={
            **self._auth(),
            "tracking_number": tracking_number,
        })
        r.raise_for_status()
        return r.json()

    def get_cities(self) -> list:
        r = requests.post(f"{self.BASE}/GetCities", json=self._auth())
        r.raise_for_status()
        return r.json()


# ══════════════════════════════════════════════════════════════════════
# LEOPARDS COURIER (Pakistan)
# ══════════════════════════════════════════════════════════════════════

class LeopardsService:
    """
    Leopards Courier Pakistan — REST API.
    Docs: https://merchantapi.leopardscourier.com
    """

    BASE = "https://merchantapi.leopardscourier.com/api"

    def __init__(self):
        self.api_key  = os.getenv("LEOPARDS_API_KEY", "")
        self.api_pass = os.getenv("LEOPARDS_API_PASSWORD", "")

    def _auth(self) -> dict:
        return {"api_key": self.api_key, "api_password": self.api_pass}

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{self.BASE}/{path}/", json={**self._auth(), **data},
                          headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()

    def book_packet(
        self,
        shipper_name: str,
        shipper_email: str,
        shipper_phone: str,
        shipper_address: str,
        shipper_city: int,             # city ID from getCities
        consignee_name: str,
        consignee_phone: str,
        consignee_address: str,
        consignee_city: int,
        shipment_type: int = 1,        # 1=normal, 2=COD
        pieces: int = 1,
        weight: float = 0.5,
        amount: float = 0,
        order_id: str = "",
    ) -> dict:
        return self._post("bookPacket", {
            "booked_packet_weight":              weight,
            "booked_packet_no_piece":            pieces,
            "booked_packet_collect_amount":      amount,
            "booked_packet_order_id":            order_id,
            "shipment_type_id":                  shipment_type,
            "origin_city":                       shipper_city,
            "destination_city":                  consignee_city,
            "booked_packet_shipper_name":        shipper_name,
            "booked_packet_shipper_email":       shipper_email,
            "booked_packet_shipper_phone":       shipper_phone,
            "booked_packet_shipper_address":     shipper_address,
            "booked_packet_consignee_name":      consignee_name,
            "booked_packet_consignee_phone":     consignee_phone,
            "booked_packet_consignee_address":   consignee_address,
        })

    def track_packet(self, tracking_number: str) -> dict:
        return self._post("trackBookedPacket", {"track_numbers": tracking_number})

    def get_cities(self) -> list:
        r = requests.get(f"{self.BASE}/getCities/",
                         params=self._auth(),
                         headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()

    def get_load_sheet(self, booking_date: str) -> dict:
        """booking_date: YYYY-MM-DD"""
        return self._post("loadSheetByDate", {"loadsheet_date": booking_date})