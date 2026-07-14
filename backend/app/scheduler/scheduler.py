"""
scheduler/scheduler.py
-----------------------
APScheduler background scheduler.
Starts automatically when FastAPI starts.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.jobs.gmail_job import check_emails
from app.services.shopify_automation import run_low_stock_sweep_all_businesses

scheduler = BackgroundScheduler(
    job_defaults={
        "coalesce": True,          # merge missed runs into one
        "max_instances": 1,        # prevent overlapping runs
        "misfire_grace_time": 30,
    }
)

# Check Gmail every 5 minutes
scheduler.add_job(
    check_emails,
    trigger="interval",
    minutes=5,
    id="gmail_check",
    replace_existing=True,
)

# Sweep every connected Shopify store for low stock every 30 minutes.
# This is the safety net alongside the real-time inventory webhook --
# it also catches stock edited by hand in Shopify admin, not just
# changes that happen through an order.
scheduler.add_job(
    run_low_stock_sweep_all_businesses,
    trigger="interval",
    minutes=30,
    id="shopify_low_stock_sweep",
    replace_existing=True,
)
