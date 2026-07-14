"""
services/auto_reply.py
----------------------
Runs the multi-agent pipeline and returns the saved reply.
"""

from app.agents.manager_agent import ManagerAgent


class AutoReplyService:

    def __init__(self):
        self.manager = ManagerAgent()

    def generate_reply(
        self,
        business_id: int,
        email_id: str,
        to_email: str,
        subject: str,
        email_text: str,
        thread_id: str = None,
    ) -> dict:

        print("=" * 60)
        print("AutoReplyService Started")
        print("Business ID :", business_id)
        print("Email ID    :", email_id)
        print("Subject     :", subject)
        print("=" * 60)

        try:

            result = self.manager.handle_email(
                business_id=business_id,
                email_id=email_id,
                to_email=to_email,
                subject=subject,
                email_text=email_text,
                thread_id=thread_id,
            )

            print("ManagerAgent completed successfully.")
            print(result)

            return result

        except Exception as e:

            print("=" * 60)
            print("AUTO REPLY SERVICE ERROR")
            print(type(e).__name__)
            print(e)
            print("=" * 60)

            raise