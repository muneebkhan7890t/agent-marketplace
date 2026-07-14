"""
services/email_processor.py
----------------------------
Fetches emails, skips already-processed ones,
runs auto-reply pipeline, marks as processed.
"""

from app.mcp.gmail import read_emails
from app.services.auto_reply import AutoReplyService
from app.services.email_memory import EmailMemory


class EmailProcessor:

    def __init__(self):
        self.auto_reply = AutoReplyService()
        self.memory = EmailMemory()

    def process_all(self, business_id: int) -> list[dict]:
        """
        Main entry point called by the scheduler / agent.
        Returns list of {email, reply} dicts for all newly processed emails.
        """

        # Fetch all emails (for testing)
        emails = read_emails(
            business_id=business_id,
            max_results=20,
            unread_only=False
        )

        results = []

        print("=" * 60)
        print(f"Fetched {len(emails)} email(s)")
        print("=" * 60)

        for email in emails:

            email_id = email["id"]

            print("-" * 60)
            print("EMAIL ID :", email_id)
            print("FROM     :", email["from_email"])
            print("SUBJECT  :", email["subject"])

            # Skip already processed emails
            if self.memory.is_processed(email_id):
                print("SKIPPED (Already Processed)")
                continue

            print("Calling AutoReplyService...")

            try:

                reply = self.auto_reply.generate_reply(
                    business_id=business_id,
                    email_id=email_id,
                    to_email=email["from_email"],
                    subject=email["subject"],
                    email_text=email["body"] or email["snippet"],
                    thread_id=email.get("thread_id"),
                )

                print("Reply generated successfully!")
                print(reply)

                # Mark email as processed
                self.memory.mark_processed(email_id)

                results.append({
                    "email": email,
                    "reply": reply
                })

            except Exception as e:

                print("=" * 60)
                print("AUTO REPLY ERROR")
                print(type(e).__name__)
                print(e)
                print("=" * 60)

        print("=" * 60)
        print(f"Finished. Generated {len(results)} reply/replies.")
        print("=" * 60)

        

        return results