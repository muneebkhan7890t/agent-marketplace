from app.ai.huggingface_client import generate_response


class EmailAI:

    def generate_reply(self, email_text):

        prompt = f"""
You are a professional customer support AI.

Customer Email:
{email_text}

Write a professional reply.
"""

        return generate_response(prompt)

    def analyze(self, prompt):
        return generate_response(prompt)