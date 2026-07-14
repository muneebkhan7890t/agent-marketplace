"""
integrations/razorpay/service.py
---------------------------------
Razorpay (India) + JazzCash (Pakistan) payments.
Paste → backend/app/integrations/razorpay/service.py

Razorpay env vars:
  RAZORPAY_KEY_ID
  RAZORPAY_KEY_SECRET

JazzCash env vars:
  JAZZCASH_MERCHANT_ID
  JAZZCASH_PASSWORD
  JAZZCASH_INTEGRITY_SALT
"""

import os
import hmac
import hashlib
import requests
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════
# RAZORPAY
# ══════════════════════════════════════════════════════════════════════

class RazorpayService:

    BASE = "https://api.razorpay.com/v1"

    def __init__(self):
        self.auth = (
            os.getenv("RAZORPAY_KEY_ID", ""),
            os.getenv("RAZORPAY_KEY_SECRET", ""),
        )

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{self.BASE}{path}", auth=self.auth, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, data: dict) -> dict:
        r = requests.post(f"{self.BASE}{path}", auth=self.auth, json=data)
        r.raise_for_status()
        return r.json()

    def create_order(self, amount_paise: int, currency: str = "INR", receipt: str = "", notes: dict = None) -> dict:
        """
        amount_paise: e.g. 50000 = ₹500
        notes: arbitrary key/value pairs Razorpay echoes back on the
        order/payment objects -- used to carry business_id/agent_id
        through to the webhook so payment.captured knows what to install.
        """
        data = {
            "amount":   amount_paise,
            "currency": currency,
            "receipt":  receipt,
        }
        if notes:
            data["notes"] = notes
        return self._post("/orders", data)

    def get_order(self, order_id: str) -> dict:
        return self._get(f"/orders/{order_id}")

    def list_orders(self, count: int = 20) -> list:
        return self._get("/orders", {"count": count}).get("items", [])

    def list_payments(self, count: int = 20) -> list:
        return self._get("/payments", {"count": count}).get("items", [])

    def get_payment(self, payment_id: str) -> dict:
        return self._get(f"/payments/{payment_id}")

    def refund_payment(self, payment_id: str, amount_paise: int = None) -> dict:
        data = {}
        if amount_paise:
            data["amount"] = amount_paise
        return self._post(f"/payments/{payment_id}/refund", data)

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify Razorpay payment signature on success callback."""
        msg = f"{order_id}|{payment_id}"
        secret = os.getenv("RAZORPAY_KEY_SECRET", "").encode()
        digest = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature)

    def get_failed_payments(self, count: int = 20) -> list:
        payments = self.list_payments(count)
        return [p for p in payments if p.get("status") == "failed"]

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str = None) -> bool:
        """
        Verify the `X-Razorpay-Signature` header on an incoming webhook
        POST (Dashboard -> Settings -> Webhooks -> Secret). This is a
        SEPARATE check from verify_signature() above, which validates the
        order_id|payment_id pair returned to the browser after checkout --
        webhooks sign the raw request body instead.
        """
        secret = (secret or os.getenv("RAZORPAY_WEBHOOK_SECRET", "")).encode()
        digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature or "")


# ══════════════════════════════════════════════════════════════════════
# JAZZCASH (Pakistan)
# ══════════════════════════════════════════════════════════════════════

class JazzCashService:
    """
    JazzCash Mobile Account / MWALLET payment initiation.
    Uses JazzCash REST API (sandbox: sandbox.jazzcash.com.pk).
    """

    def __init__(self, sandbox: bool = True):
        self.merchant_id    = os.getenv("JAZZCASH_MERCHANT_ID", "")
        self.password       = os.getenv("JAZZCASH_PASSWORD", "")
        self.integrity_salt = os.getenv("JAZZCASH_INTEGRITY_SALT", "")
        self.base = (
            "https://sandbox.jazzcash.com.pk/ApplicationAPI/API"
            if sandbox else
            "https://payments.jazzcash.com.pk/ApplicationAPI/API"
        )

    def _hash(self, data: dict) -> str:
        """Build HMAC-SHA256 secure hash from sorted values."""
        sorted_vals = "&".join(
            str(v) for k, v in sorted(data.items()) if k != "pp_SecureHash"
        )
        msg = f"{self.integrity_salt}&{sorted_vals}"
        return hmac.new(
            self.integrity_salt.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

    def initiate_payment(
        self,
        txn_ref_no: str,
        amount_pkr: int,
        mobile_no: str,
        description: str = "AgentHub Payment",
    ) -> dict:
        """
        Initiate a mobile wallet (MWALLET) payment.
        amount_pkr: in PKR e.g. 500
        mobile_no:  03xxxxxxxxx
        """
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        data = {
            "pp_Version":        "1.1",
            "pp_TxnType":        "MWALLET",
            "pp_Language":       "EN",
            "pp_MerchantID":     self.merchant_id,
            "pp_Password":       self.password,
            "pp_TxnRefNo":       txn_ref_no,
            "pp_Amount":         str(amount_pkr * 100),   # in paisas
            "pp_TxnCurrency":    "PKR",
            "pp_TxnDateTime":    now,
            "pp_BillReference":  txn_ref_no,
            "pp_Description":    description,
            "pp_TxnExpiryDateTime": now[:8] + "235959",
            "pp_MobileNumber":   mobile_no,
        }
        data["pp_SecureHash"] = self._hash(data)

        r = requests.post(
            f"{self.base}/2.0/Purchase/DoMWalletTransaction",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    def inquiry(self, txn_ref_no: str) -> dict:
        """Check the status of a transaction."""
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        data = {
            "pp_Version":     "1.1",
            "pp_TxnType":     "MWALLET",
            "pp_Language":    "EN",
            "pp_MerchantID":  self.merchant_id,
            "pp_Password":    self.password,
            "pp_TxnRefNo":    txn_ref_no,
            "pp_TxnDateTime": now,
        }
        data["pp_SecureHash"] = self._hash(data)
        r = requests.post(
            f"{self.base}/2.0/Purchase/PaymentInquiry",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()