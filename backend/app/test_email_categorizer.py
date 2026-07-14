from app.services.email_categorizer import EmailCategorizer

service = EmailCategorizer()

email = """
Hello,

I bought your AI Agent yesterday.

It is not working.

Can you help me?

Thanks.
"""

category = service.categorize(email)

print(category)