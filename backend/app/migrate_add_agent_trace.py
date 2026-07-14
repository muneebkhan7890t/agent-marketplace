"""
migrate_add_agent_trace.py
----------------------------
One-off migration: adds the `agent_trace` column to the existing `replies`
table (needed for the new multi-agent pipeline's transparency trace).

Run once:
    cd backend/app
    python migrate_add_agent_trace.py
"""

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE replies ADD COLUMN IF NOT EXISTS agent_trace TEXT;"
    ))
    conn.commit()

print("Migration complete: replies.agent_trace added.")
