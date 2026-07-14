"""
mcp/google_sheets.py
Paste → backend/app/mcp/google_sheets.py
"""
from app.integrations.google_sheets.service import GoogleSheetsService
_svc = None
def _s(): global _svc; _svc = _svc or GoogleSheetsService(); return _svc

def read(spreadsheet_id: str, range_: str) -> list:               return _s().read(spreadsheet_id, range_)
def get_all_rows(spreadsheet_id: str, sheet: str = "Sheet1") -> list: return _s().get_all_rows(spreadsheet_id, sheet)
def append_row(spreadsheet_id: str, range_: str, values: list) -> dict: return _s().append_row(spreadsheet_id, range_, values)
def append_rows(spreadsheet_id: str, range_: str, rows: list) -> dict:  return _s().append_rows(spreadsheet_id, range_, rows)
def export_orders(spreadsheet_id: str, orders: list) -> dict:     return _s().export_orders(spreadsheet_id, orders)
def export_weekly_summary(spreadsheet_id: str, summary: dict) -> dict:  return _s().export_weekly_summary(spreadsheet_id, summary)






