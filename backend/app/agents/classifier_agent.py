"""
agents/classifier_agent.py
----------------------------
Email Classifier Agent.

First stop in the pipeline: reads the email and decides two things:
  1. `category`   -- the fine-grained label used everywhere else in the app
                     (Sales, Refund, Support, Billing, Complaint, Feedback,
                     Order Status, Technical, Spam, General) -- unchanged from
                     the existing EmailCategorizer so nothing downstream breaks.
  2. `route`      -- which SPECIALIST agent should own this email:
                     "sales" | "refund" | "support"
                     Everything that isn't clearly Sales or Refund defaults
                     to Support, since a generic helpful-and-polite specialist
                     is the safest fallback for Billing/Complaint/Feedback/
                     Order Status/Technical/General/Spam.
"""

from app.services.email_categorizer import EmailCategorizer

ROUTE_MAP = {
    "sales": "sales",
    "refund": "refund",
}


class EmailClassifierAgent:

    def __init__(self):
        self.categorizer = EmailCategorizer()

    def classify(self, email_text: str) -> dict:
        category = self.categorizer.categorize(email_text)
        route = ROUTE_MAP.get(category.strip().lower(), "support")

        return {
            "category": category,
            "route": route,
        }
