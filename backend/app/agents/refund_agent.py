"""
agents/refund_agent.py
-------------------------
Refund Agent (specialist).

Reads a Refund-category email and produces a brief for the Writer. This
agent does NOT decide whether to actually issue the refund -- that stays
with the Action Agent + a human approval step (see services/ai_actions.py).
Its job here is purely to shape a good, empathetic reply while the refund
itself is proposed separately for approval.
"""

from app.ai.huggingface_client import generate_response


class RefundAgent:

    role_prompt = "You are an empathetic billing specialist handling a refund request."

    def build_brief(self, email_text: str, history_text: str = "") -> dict:
        history_block = f"\n\nConversation so far:\n{history_text}" if history_text else ""

        prompt = f"""
You are a refunds triage specialist. Read the customer's email and produce a
short brief for the person who will write the actual reply.

Customer email:
{email_text}{history_block}

Respond with 2-4 short bullet points (no more) covering:
- the stated reason for the refund request
- whether an amount was mentioned
- the right tone (apologetic, neutral, etc.) given how the customer wrote

Keep it terse -- this is an internal note, not the reply itself. Do not
confirm the refund has been approved or issued -- that is decided
separately by a human reviewer.
"""
        checklist_text = generate_response(prompt)

        return {
            "role_prompt": self.role_prompt,
            "checklist": checklist_text.strip(),
        }
