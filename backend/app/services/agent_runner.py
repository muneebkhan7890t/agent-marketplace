from app.services.gmail_service import GmailService
from app.agents.customer_support import CustomerSupportAgent


class AgentRunner:

    def __init__(self):
        self.gmail = GmailService()
        self.agent = CustomerSupportAgent()

    def run(self):

        emails = self.gmail.get_new_emails()

        results = []

        # If Gmail returns no emails
        if not emails:
            return []

        # Process every email
        for email in emails:

            # Get the email body safely
            body = ""

            if isinstance(email, dict):
                body = email.get("snippet", "")

            response = self.agent.process_email(body)

            results.append(
                {
                    "email": body,
                    "reply": response
                }
            )

        return results