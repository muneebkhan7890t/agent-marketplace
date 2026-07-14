from app.database import Base
from app.database import engine

from app.models.user import User
from app.models.business import Business
from app.models.agent import Agent
from app.models.installed_agent import InstalledAgent
from app.models.mcp_connection import MCPConnection
from app.models.installation import AgentInstallation
from app.models.agent import Agent
from app.models.purchase import Purchase
from app.models.agent_log import AgentLog
from app.whatsapp_suite import WhatsAppMessage, WhatsAppPlaybookInstall, WhatsAppAuditLog  # Phase 3/8/9/10 tables

Base.metadata.create_all(bind=engine)

print("Tables Created")