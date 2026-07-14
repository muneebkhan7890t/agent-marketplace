from app.ai.huggingface_client import generate_response

class CustomerSupportAgent:

    def process_email(
        self,
        email_text
    ):

        prompt = f"""
        Customer Email:

        {email_text}

        Write a helpful reply.
        """

        return generate_response(
            prompt
        )
