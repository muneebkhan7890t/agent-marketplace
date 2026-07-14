from app.agents.customer_support import CustomerSupportAgent

agent = CustomerSupportAgent()

response = agent.process_email(
    """
    Hello,
    I have not received my order.
    """
)

print(response)