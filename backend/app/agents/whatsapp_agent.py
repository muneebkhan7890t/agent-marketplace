"""
agents/whatsapp_agent.py  (superseded)
-----------------------------------------
The WhatsApp agent pipeline now lives in app/whatsapp_suite.py as
`WhatsAppManager` (Phase 6: multi-agent orchestration). Kept as a thin
compat alias so any existing `from app.agents.whatsapp_agent import
WhatsAppAgent` import keeps working.
"""

from app.whatsapp_suite import WhatsAppManager as WhatsAppAgent  # noqa: F401
