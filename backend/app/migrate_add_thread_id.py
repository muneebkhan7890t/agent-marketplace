"""
migrate_add_thread_id.py
-------------------------
One-off migration: adds the new `thread_id` column to the existing
`replies` table (create_tables.py's Base.metadata.create_all() only creates
tables that don't exist yet -- it will NOT add a column to a table that's
already there).

Run once:
    cd backend/app
    python migrate_add_thread_id.py
"""

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE replies ADD COLUMN IF NOT EXISTS thread_id VARCHAR;"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_replies_thread_id ON replies (thread_id);"
    ))
    conn.commit()

print("Migration complete: replies.thread_id added.")
