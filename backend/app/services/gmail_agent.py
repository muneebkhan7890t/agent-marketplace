from app.runtime.gmail_runtime import GmailRuntime


class GmailAgent:

    def __init__(self):

        self.runtime = GmailRuntime()

    def start(self, business_id):

        print("=" * 50)
        print("Starting Gmail AI Agent...")
        print("=" * 50)

        results = self.runtime.run(business_id)

        print("=" * 50)
        print("Gmail AI Agent Finished")
        print("=" * 50)

        return results