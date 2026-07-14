from app.services.auto_reply import AutoReplyService

BUSINESS_ID = 1
service = AutoReplyService()

result = service.generate_reply(
    BUSINESS_ID,
    "your_email@gmail.com",
    "Testing AI",
    "Hello, I would like more information about your AI agent."
)

print(result)