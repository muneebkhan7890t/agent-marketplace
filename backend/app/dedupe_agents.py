"""
dedupe_agents.py
-----------------
One-time cleanup for an already-running database that has duplicate rows
in the `agents` table (e.g. from calling POST /agents/seed multiple times
before the idempotency fix in routes/agents.py).

This does NOT just change code — it directly fixes the data already sitting
in your Postgres database, which is why the marketplace kept showing
duplicates / missing the WhatsApp agent even after the code was updated:
a code fix alone cannot remove rows that already exist.

Usage (from backend/app, with your venv active and DATABASE_URL set the
same way your API uses it):

    python dedupe_agents.py

What it does, in order:
  1. Finds every agent name that has more than one row.
  2. Keeps the oldest (lowest id) row for that name.
  3. Re-points any installed_agents rows that reference a duplicate's id
     over to the kept id (so no business loses their "installed" agent).
  4. Deletes the now-unreferenced duplicate agent rows.
  5. Inserts any of the 4 default agents (including "WhatsApp Support
     Agent") that are still missing entirely.
"""

from sqlalchemy import text
from app.database import SessionLocal
from app.models.agent import Agent
from app.models.installed_agent import InstalledAgent
from app.routes.agents import DEFAULT_AGENTS  # single source of truth — was a second,
                                               # separately-maintained copy that had
                                               # already drifted out of sync


def dedupe():
    db = SessionLocal()
    try:
        all_agents = db.query(Agent).order_by(Agent.id.asc()).all()

        by_name = {}
        for agent in all_agents:
            by_name.setdefault(agent.name, []).append(agent)

        removed = 0
        for name, rows in by_name.items():
            if len(rows) <= 1:
                continue

            keep = rows[0]  # oldest row (lowest id)
            duplicates = rows[1:]

            print(f"'{name}': keeping id={keep.id}, removing {[d.id for d in duplicates]}")

            for dup in duplicates:
                # Re-point any installs so nobody's installed agent disappears.
                db.query(InstalledAgent).filter(
                    InstalledAgent.agent_id == dup.id
                ).update({InstalledAgent.agent_id: keep.id})

                db.delete(dup)
                removed += 1

        db.commit()
        print(f"Removed {removed} duplicate agent row(s).")

        # Add any of the 4 default agents that are still completely missing.
        added = []
        for agent_data in DEFAULT_AGENTS:
            exists = db.query(Agent).filter(Agent.name == agent_data["name"]).first()
            if not exists:
                db.add(Agent(**agent_data))
                added.append(agent_data["name"])

        db.commit()
        print(f"Added missing default agents: {added or 'none'}")

    finally:
        db.close()


if __name__ == "__main__":
    dedupe()
