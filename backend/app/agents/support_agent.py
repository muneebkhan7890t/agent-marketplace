"""
agents/support_agent.py
--------------------------
Support Agent (specialist).

Doesn't write the customer-facing reply itself -- it reads the email
(+ conversation history) and produces a short BRIEF: what the Writer Agent
needs to address, in what tone, and what to avoid. Keeping "understand the
problem" and "write good prose" as separate steps is what makes a
multi-agent pipeline more reliable than one giant prompt.
"""

from app.ai.huggingface_client import generate_response


class SupportAgent:

    role_prompt = "You are a helpful, patient customer support representative."

    def build_brief(self, email_text: str, history_text: str = "") -> dict:
        history_block = f"\n\nConversation so far:\n{history_text}" if history_text else ""

        prompt = f"""
You are a customer support triage specialist. Read the customer's email and
produce a short brief for the person who will write the actual reply.

Customer email:
{email_text}{history_block}

Respond with 2-4 short bullet points (no more) covering:
- what the customer actually needs
- any missing information that should be asked for, if applicable
- anything that needs to be handled carefully (frustration, urgency, etc.)

Keep it terse -- this is an internal note, not the reply itself.
"""
        checklist_text = generate_response(prompt)

        return {
            "role_prompt": self.role_prompt,
            "checklist": checklist_text.strip(),
        }
