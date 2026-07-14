from app.services.email_ai import EmailAI
ai = EmailAI()

email = """
Write only a professional email reply.

Customer email:
Hi, I purchased your AI Agent yesterday, but it is not working. Please help.

Do not give multiple options.
Do not explain your reasoning.
Do not include tips.
Return only the email.
"""

reply = ai.generate_reply(email)

print(reply)