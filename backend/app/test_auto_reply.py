from app.services.auto_reply import AutoReplyService

service = AutoReplyService()

BUSINESS_ID = 1
result = service.generate_reply(
    access_token=BUSINESS_ID ,
    to_email="your_email@gmail.com",
    subject="Testing Auto Reply",
    email_text="Hi, I bought your AI Agent yesterday but it is not working."
)

print(result)

