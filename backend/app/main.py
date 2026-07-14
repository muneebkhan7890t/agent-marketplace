"""
main.py
-------
backend/app/main.py
"""
from app.error_tracking import init_sentry
init_sentry()  # first, so startup failures and every route below are captured

import app.models as _models  # noqa — load all models first, prevents circular imports

from app.database import Base, engine
Base.metadata.create_all(bind=engine)
print("Creating database tables...")
print(Base.metadata.tables.keys())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler.scheduler import scheduler

from app.routes.auth             import router as auth_router
from app.routes.business         import router as business_router
from app.routes.gmail            import router as gmail_router
from app.routes.reply            import router as reply_router
from app.routes.actions          import router as actions_router
from app.routes.marketplace      import router as marketplace_router
from app.routes.agents           import router as agents_router
from app.routes.purchases        import router as purchase_router
from app.routes.runtime          import router as runtime_router
from app.routes.dashboard        import router as dashboard_router
from app.routes.analytics        import router as analytics_router
from app.routes.logs             import router as logs_router
from app.routes.email_agent      import router as email_router
from app.routes.shopify          import router as shopify_router
from app.routes.shopify_webhooks import router as shopify_webhooks_router
from app.routes.woocommerce      import router as woo_router
from app.routes.amazon           import router as amazon_router
from app.whatsapp_suite          import router as whatsapp_router
from app.routes.stripe           import router as stripe_router
from app.routes.razorpay         import router as razorpay_router
from app.routes.razorpay_webhooks import router as razorpay_webhooks_router
from app.routes.shipping         import router as shipping_router
from app.routes.hubspot          import router as hubspot_router
from app.routes.mailchimps       import router as mailchimp_router
from app.routes.meta_ads         import router as meta_router
from app.routes.google_sheet     import router as sheets_router
from app.routes.knowledge        import router as knowledge_router
from app.routes.admin_agents     import router as admin_agents_router
from app.routes.agent_actions    import router as agent_actions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    print("[App] APScheduler started")
    yield
    scheduler.shutdown()
    print("[App] APScheduler stopped")


app = FastAPI(
    title="AgentHub API",
    description="AI Agent Marketplace Backend",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "null", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AgentHub API", "status": "running", "version": "2.0.0"}


# ── Core ──────────────────────────────────────────────────────────────
app.include_router(auth_router,        prefix="/auth",          tags=["Auth"])
app.include_router(business_router,    prefix="/businesses",    tags=["Businesses"])
app.include_router(dashboard_router,   prefix="/dashboard",     tags=["Dashboard"])
app.include_router(analytics_router,   prefix="/analytics",     tags=["Analytics"])
app.include_router(agents_router,      prefix="/agents",        tags=["Agents"])
app.include_router(marketplace_router, prefix="/marketplace",   tags=["Marketplace"])
app.include_router(purchase_router,    prefix="/purchases",     tags=["Purchases"])
app.include_router(runtime_router,     prefix="/runtime",       tags=["Runtime"])
app.include_router(logs_router,        prefix="/logs",          tags=["Logs"])

# ── Communication ─────────────────────────────────────────────────────
app.include_router(gmail_router,       prefix="/gmail",         tags=["Gmail"])
app.include_router(reply_router,       prefix="/replies",       tags=["Replies"])
app.include_router(actions_router,     prefix="/actions",       tags=["AI Actions"])
app.include_router(email_router,       prefix="/email-agent",   tags=["Email Agent"])
app.include_router(whatsapp_router,    prefix="/whatsapp",      tags=["WhatsApp"])

# ── Ecommerce ─────────────────────────────────────────────────────────
app.include_router(shopify_router,          prefix="/shopify",          tags=["Shopify"])
app.include_router(shopify_webhooks_router, prefix="/shopify/webhooks", tags=["Shopify Webhooks"])
app.include_router(woo_router,              prefix="/woocommerce",      tags=["WooCommerce"])
app.include_router(amazon_router,           prefix="/amazon",           tags=["Amazon"])

# ── Payments ──────────────────────────────────────────────────────────
app.include_router(stripe_router,      prefix="/stripe",        tags=["Stripe"])
app.include_router(razorpay_router,    prefix="/razorpay",      tags=["Razorpay / JazzCash"])
app.include_router(razorpay_webhooks_router, prefix="/razorpay/webhooks", tags=["Razorpay Webhooks"])

# ── Shipping ──────────────────────────────────────────────────────────
app.include_router(shipping_router,    prefix="/shipping",      tags=["Shipping"])

# ── Marketing / CRM ───────────────────────────────────────────────────
app.include_router(hubspot_router,     prefix="/hubspot",       tags=["HubSpot"])
app.include_router(mailchimp_router,   prefix="/mailchimp",     tags=["Mailchimp"])
app.include_router(meta_router,        prefix="/meta-ads",      tags=["Meta Ads"])
app.include_router(sheets_router,      prefix="/sheets",        tags=["Google Sheets"])
app.include_router(knowledge_router,   prefix="/knowledge",     tags=["Knowledge Base"])

# ── Admin ─────────────────────────────────────────────────────────────
app.include_router(admin_agents_router, prefix="/admin/agents", tags=["Admin: Agents"])

# ── The 7 new agents' execution endpoints ────────────────────────────
app.include_router(agent_actions_router, prefix="/agent-actions", tags=["Agent Actions"])