"""
migrate_add_whatsapp_fields.py
-------------------------------
One-off migration: adds the WhatsApp connection columns to the existing
`businesses` table (create_tables.py's Base.metadata.create_all() only
creates tables that don't exist yet -- it will NOT add a column to a
table that's already there).

Adds:
  whatsapp_business_number  -- the human-readable number the user typed
                               in on the "Connect WhatsApp" screen
  whatsapp_phone_id         -- Meta "Phone Number ID" (used to call the
                               Cloud API and to route incoming webhooks
                               back to the right business)
  whatsapp_token            -- permanent system-user access token
  whatsapp_connected        -- bool flag used everywhere else in the app

Run once:
    cd backend/app
    python migrate_add_whatsapp_fields.py
"""

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_business_number VARCHAR;"
    ))
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_phone_id VARCHAR;"
    ))
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_token TEXT;"
    ))
    conn.execute(text(
        "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS whatsapp_connected BOOLEAN DEFAULT FALSE;"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_businesses_whatsapp_phone_id ON businesses (whatsapp_phone_id);"
    ))
    conn.commit()

print("Migration complete: businesses.whatsapp_business_number / whatsapp_phone_id / "
      "whatsapp_token / whatsapp_connected added.")
