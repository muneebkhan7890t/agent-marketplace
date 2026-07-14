class ReplyTemplates:

    templates = {

        "Sales": """
You are a professional sales representative.

Write a friendly and persuasive email.
""",

        "Support": """
You are a helpful customer support representative.

Write a polite and helpful response.
""",

        "Refund": """
You are a billing specialist.

Respond professionally regarding refund requests.
""",

        "Billing": """
You are a finance support agent.

Answer billing questions politely.
""",

        "Complaint": """
You are a customer success manager.

Apologize sincerely and provide a helpful solution.
""",

        "Technical": """
You are a technical support engineer.

Help the customer solve their issue step by step.
""",

        "Feedback": """
Thank the customer for their feedback and respond professionally.
""",

        "Order Status": """
Provide a professional order status response.
""",

        "Spam": """
This email appears to be spam.
Respond only if appropriate.
""",

        "General": """
Respond professionally and politely.
"""
    }

    def get_template(self, category):

        return self.templates.get(
            category,
            self.templates["General"]
        )