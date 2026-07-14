"""
migrate_add_admin_field.py
----------------------------
One-off migration: adds `users.is_admin` to an existing database
(create_tables.py's Base.metadata.create_all() only creates tables that
don't exist yet -- it will NOT add a column to a table that's already
there).

This column gates the new /admin/agents catalog-management endpoints
(routes/admin_agents.py) -- letting someone add/edit/remove marketplace
agents without touching code or redeploying.

Run once:
    cd backend/app
    python migrate_add_admin_field.py

Then promote yourself:
    UPDATE users SET is_admin = TRUE WHERE email = 'you@example.com';
"""

from sqlalchemy import text
from app.database import engine

with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"
    ))
    conn.commit()

print("Migration complete: users.is_admin added (defaults to FALSE for everyone).")
