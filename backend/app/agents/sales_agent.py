"""
agents/sales_agent.py
------------------------
Sales Agent (specialist).

Reads a Sales-category email and produces a brief that steers the Writer
toward a persuasive-but-honest reply: what the prospect is interested in,
what to highlight, and what NOT to promise (pricing/features the AI isn't
certain about).
"""

from app.ai.huggingface_client import generate_response


class SalesAgent:

    role_prompt = "You are a friendly, persuasive but honest sales representative."

    def build_brief(self, email_text: str, history_text: str = "") -> dict:
        history_block = f"\n\nConversation so far:\n{history_text}" if history_text else ""

        prompt = f"""
You are a sales triage specialist. Read the prospect's email and produce a
short brief for the person who will write the actual reply.

Prospect email:
{email_text}{history_block}

Respond with 2-4 short bullet points (no more) covering:
- what the prospect is actually interested in / asking about
- the strongest honest selling point to lead with
- anything the reply should NOT promise (specific prices, discounts, or
  features unless already confirmed in the conversation)

Keep it terse -- this is an internal note, not the reply itself.
"""
        checklist_text = generate_response(prompt)

        return {
            "role_prompt": self.role_prompt,
            "checklist": checklist_text.strip(),
        }
