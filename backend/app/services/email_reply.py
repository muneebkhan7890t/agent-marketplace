from app.agents.customer_support import (
    CustomerSupportAgent
)


def generate_reply(
    email_text
):

    agent = CustomerSupportAgent()

    return agent.process_email(
        email_text
    )