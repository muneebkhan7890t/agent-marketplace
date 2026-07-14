"""
mcp/razorpay.py
Paste → backend/app/mcp/razorpay.py
"""
from app.integrations.razorpay.service import RazorpayService, JazzCashService

_rz = None
_jc = None
def _r() -> RazorpayService:
    global _rz
    if not _rz: _rz = RazorpayService()
    return _rz
def _j() -> JazzCashService:
    global _jc
    if not _jc: _jc = JazzCashService()
    return _jc

# Razorpay
def create_order(amount_paise: int, currency: str = "INR", receipt: str = "", notes: dict = None) -> dict:
    return _r().create_order(amount_paise, currency, receipt, notes)
def get_payment(payment_id: str) -> dict:        return _r().get_payment(payment_id)
def refund_payment(payment_id: str, amount: int = None) -> dict: return _r().refund_payment(payment_id, amount)
def get_failed_payments(count: int = 20) -> list: return _r().get_failed_payments(count)
def verify_signature(order_id: str, payment_id: str, sig: str) -> bool:
    return _r().verify_signature(order_id, payment_id, sig)

# JazzCash
def jazzcash_pay(txn_ref: str, amount_pkr: int, mobile: str, description: str = "") -> dict:
    return _j().initiate_payment(txn_ref, amount_pkr, mobile, description)
def jazzcash_inquiry(txn_ref: str) -> dict:      return _j().inquiry(txn_ref)