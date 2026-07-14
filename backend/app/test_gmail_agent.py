from app.services.gmail_agent import GmailAgent

BUSINESS_ID = 1
agent = GmailAgent()

results = agent.start(BUSINESS_ID)

print(results)