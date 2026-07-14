"""
agents/action_agent.py
-------------------------
Action Agent.

Decides whether this email implies a concrete action (refund, support
ticket) and proposes it -- it never executes anything itself. This wraps
the existing services/ai_actions.py (built for the standalone "AI actions"
feature) so the multi-agent pipeline and the simpler pipeline share one
execution path and one human-approval gate.
"""

from app.services.ai_action import AIActionService


class ActionAgent:

    def __init__(self):
        self.service = AIActionService()

    def propose(
        self,
        business_id: int,
        reply_id: int,
        email_id: str,
        thread_id: str,
        to_email: str,
        subject: str,
        email_text: str,
        category: str,
    ) -> list:
        return self.service.detect_and_propose(
            business_id=business_id,
            reply_id=reply_id,
            email_id=email_id,
            thread_id=thread_id,
            to_email=to_email,
            subject=subject,
            email_text=email_text,
            category=category,
        )
