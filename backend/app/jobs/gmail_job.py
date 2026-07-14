"""
jobs/gmail_job.py
-----------------
Scheduled job: poll Gmail for all connected businesses, run AI pipeline.
"""

from app.services.gmail_agent import GmailAgent
from app.database import SessionLocal
from app.models.business import Business
from app.logs.logger import AgentLogger
from app.error_tracking import capture_exception


def check_emails():
    """
    Called by APScheduler every N minutes.
    Iterates over ALL businesses with Gmail connected (not just the first one).
    """
    print("[GmailJob] Starting scheduled email check...")

    db = SessionLocal()
    logger = AgentLogger()

    try:
        businesses = db.query(Business).filter(
            Business.gmail_connected == True
        ).all()

        if not businesses:
            print("[GmailJob] No businesses with Gmail connected.")
            return

        agent = GmailAgent()

        for business in businesses:
            try:
                print(f"[GmailJob] Processing business_id={business.id} ({business.business_name})")
                results = agent.start(business.id)
                logger.log(
                    business_id=business.id,
                    message=f"Processed {len(results)} email(s)",
                )
            except Exception as exc:
                print(f"[GmailJob] Error for business_id={business.id}: {exc}")
                capture_exception(exc, context={"job": "gmail_check", "business_id": business.id})
                logger.log(
                    business_id=business.id,
                    message=f"Error during email check: {exc}",
                )

    finally:
        db.close()

    print("[GmailJob] Done.")
