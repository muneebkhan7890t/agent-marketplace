from app.ai.huggingface_client import generate_response


class EmailCategorizer:

    def categorize(self, email_text):

        prompt = f"""
You are an AI email classifier.

Classify the following email into ONLY ONE category.

Categories:

- Sales
- Refund
- Support
- Billing
- Complaint
- Feedback
- Order Status
- Technical
- Spam
- General

Email:

{email_text}

Return ONLY the category name.
"""

        category = generate_response(prompt)

        return category.strip()