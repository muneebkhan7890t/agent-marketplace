"""
migrate_add_shopify_automation_fields.py
------------------------------------------
One-off migration: adds the columns the Shopify automation pipeline needs
to the existing `businesses` table (create_tables.py's
Base.metadata.create_all() only creates NEW tables -- it will NOT add a
column to a table that already exists).

Adds:
  shopify_low_stock_threshold  -- qty at/below which a product counts as
                                   "low stock" for this business (default 5)
  owner_alert_whatsapp         -- merchant's OWN WhatsApp number, where
                                   order + low-stock alerts are sent
  owner_alert_email            -- optional override email for alerts;
                                   if blank, falls back to the business's
                                   connected Gmail address

Run once:
    cd backend/app
    python migrate_add_shopify_automation_fields.py
"""

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS shopify_low_stock_threshold INTEGER DEFAULT 5;"
    ))
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_alert_whatsapp VARCHAR;"
    ))
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS owner_alert_email VARCHAR;"
    ))
    conn.commit()

print("Migration complete: businesses.shopify_low_stock_threshold / "
      "owner_alert_whatsapp / owner_alert_email added.")
