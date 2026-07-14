"""
integrations/google_sheets/service.py
---------------------------------------
Google Sheets integration via Google Sheets API v4.
Paste → backend/app/integrations/google_sheets/service.py

Uses a service account JSON key file (no OAuth needed for server-side).

Env vars:
  GOOGLE_SERVICE_ACCOUNT_JSON   ← path to service account JSON file
  OR
  GOOGLE_SERVICE_ACCOUNT_INFO   ← JSON string of the service account

Setup:
  1. Go to Google Cloud Console → IAM → Service Accounts → Create
  2. Download JSON key
  3. Share your Google Sheet with the service account email
"""

import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials() -> Credentials:
    info_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")
    if info_str:
        info = json.loads(info_str)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
    return Credentials.from_service_account_file(path, scopes=SCOPES)


class GoogleSheetsService:

    def __init__(self):
        creds = _get_credentials()
        self.service = build("sheets", "v4", credentials=creds)
        self.sheets  = self.service.spreadsheets()

    # ── Reading ───────────────────────────────────────────────────────

    def read(self, spreadsheet_id: str, range_: str) -> list[list]:
        """Read cells. range_ e.g. 'Sheet1!A1:E100'"""
        result = self.sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_,
        ).execute()
        return result.get("values", [])

    def get_all_rows(self, spreadsheet_id: str, sheet_name: str = "Sheet1") -> list[dict]:
        """Read all rows and return list of dicts using first row as headers."""
        rows = self.read(spreadsheet_id, f"{sheet_name}!A:Z")
        if not rows:
            return []
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]

    # ── Writing ───────────────────────────────────────────────────────

    def append_row(self, spreadsheet_id: str, range_: str, values: list) -> dict:
        """Append a single row. values = [col1, col2, col3, ...]"""
        return self.sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [values]},
        ).execute()

    def append_rows(self, spreadsheet_id: str, range_: str, rows: list[list]) -> dict:
        """Append multiple rows at once."""
        return self.sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

    def update_cell(self, spreadsheet_id: str, range_: str, value) -> dict:
        """Update a single cell. range_ e.g. 'Sheet1!B5'"""
        return self.sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_,
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]},
        ).execute()

    def clear_range(self, spreadsheet_id: str, range_: str) -> dict:
        return self.sheets.values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_,
        ).execute()

    # ── Sheet management ──────────────────────────────────────────────

    def create_sheet(self, spreadsheet_id: str, title: str) -> dict:
        return self.sheets.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()

    def get_sheet_names(self, spreadsheet_id: str) -> list[str]:
        meta = self.sheets.get(spreadsheetId=spreadsheet_id).execute()
        return [s["properties"]["title"] for s in meta.get("sheets", [])]

    # ── Business helpers ──────────────────────────────────────────────

    def export_orders(self, spreadsheet_id: str, orders: list[dict], sheet_name: str = "Orders") -> dict:
        """Dump a list of order dicts to a sheet (overwrites from row 2)."""
        if not orders:
            return {}
        headers = list(orders[0].keys())
        rows = [list(o.values()) for o in orders]
        self.update_cell(spreadsheet_id, f"{sheet_name}!A1", "")
        self.append_rows(spreadsheet_id, f"{sheet_name}!A1", [headers] + rows)
        return {"exported": len(orders)}

    def export_weekly_summary(self, spreadsheet_id: str, summary: dict) -> dict:
        """Write a weekly business summary row."""
        from datetime import date
        row = [
            str(date.today()),
            summary.get("total_orders", 0),
            summary.get("total_revenue", 0),
            summary.get("new_customers", 0),
            summary.get("emails_handled", 0),
            summary.get("ai_replies_sent", 0),
        ]
        return self.append_row(spreadsheet_id, "Summary!A:F", row)