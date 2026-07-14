"""
logs/logger.py
--------------
Structured agent activity logger — writes to stdout + DB.
"""

from datetime import datetime
from app.database import SessionLocal
from app.models.agent_log import AgentLog


class AgentLogger:

    def log(
        self,
        message: str,
        business_id: int = 1,
        agent_id: int = 1,
        output: str = "",
    ):
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [BIZ={business_id}] {message}")

        db = SessionLocal()
        try:
            log = AgentLog(
                business_id=business_id,
                agent_id=agent_id,
                input_text=message,
                output_text=output,
            )
            db.add(log)
            db.commit()
        except Exception as exc:
            print(f"[AgentLogger] DB write failed: {exc}")
        finally:
            db.close()
