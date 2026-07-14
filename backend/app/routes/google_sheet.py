"""
routes/google_sheets.py
Paste → backend/app/routes/google_sheets.py
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.mcp import google_sheets as gs

router = APIRouter()

class AppendRow(BaseModel):
    spreadsheet_id: str; range_: str; values: list

class ExportOrders(BaseModel):
    spreadsheet_id: str; orders: list; sheet_name: str = "Orders"

@router.get("/read")
def read(spreadsheet_id: str, range_: str):
    try:    return {"data": gs.read(spreadsheet_id, range_)}
    except Exception as e: raise HTTPException(500, str(e))

@router.get("/rows")
def rows(spreadsheet_id: str, sheet: str = "Sheet1"):
    try:    return {"rows": gs.get_all_rows(spreadsheet_id, sheet)}
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/append")
def append(body: AppendRow):
    try:    return gs.append_row(body.spreadsheet_id, body.range_, body.values)
    except Exception as e: raise HTTPException(500, str(e))

@router.post("/export-orders")
def export(body: ExportOrders):
    try:    return gs.export_orders(body.spreadsheet_id, body.orders, body.sheet_name)
    except Exception as e: raise HTTPException(500, str(e))