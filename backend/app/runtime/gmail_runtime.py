from app.services.email_processor import EmailProcessor


class GmailRuntime:

    def __init__(self):

        self.processor = EmailProcessor()

    def run(self, business_id):

        print("========== Gmail Agent ==========")

        results = self.processor.process_all(
            business_id
        )

        print(f"Processed {len(results)} email(s).")

        return results