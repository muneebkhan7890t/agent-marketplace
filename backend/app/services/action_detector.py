"""
services/action_detector.py
-----------------------------
Looks at a customer email (+ its category from EmailCategorizer) and decides
whether it implies a concrete business action -- a refund request, a support
ticket -- and if so, extracts the parameters (amount, reason, priority) the
action needs.

This never executes anything. It only produces a proposal that
services/ai_actions.py turns into a pending AgentAction row for a human to
approve.
"""

import json
import re

from app.ai.huggingface_client import generate_response

REFUND_CATEGORIES = {"refund"}
TICKET_CATEGORIES = {"complaint", "technical", "billing"}


class ActionDetector:

    def detect(self, email_text: str, category: str) -> list:
        """
        Returns a list of proposed actions, e.g.:
            [{"type": "refund", "reason": "damaged item", "amount_cents": 2500}]
            [{"type": "create_ticket", "priority": "high", "summary": "..."}]
            []  -- no action needed, a normal reply is enough
        """
        category_norm = (category or "").strip().lower()

        actions = []

        if category_norm in REFUND_CATEGORIES:
            actions.append(self._extract_refund(email_text))

        if category_norm in TICKET_CATEGORIES:
            actions.append(self._extract_ticket(email_text, category_norm))

        return [a for a in actions if a]

    # ------------------------------------------------------------------ #

    def _extract_refund(self, email_text: str) -> dict:
        prompt = f"""
You are analyzing a customer email that has been categorized as a refund request.

Email:
{email_text}

Respond with ONLY a JSON object (no markdown, no commentary) in this exact shape:
{{"reason": "<short reason for the refund>", "amount_cents": <integer or null if not mentioned>}}

If a dollar amount is mentioned, convert it to cents (e.g. $49.99 -> 4999).
If no amount is mentioned, use null.
"""
        raw = generate_response(prompt)
        parsed = self._safe_json(raw)

        return {
            "type": "refund",
            "reason": (parsed.get("reason") if parsed else None) or "Customer requested a refund",
            "amount_cents": parsed.get("amount_cents") if parsed else None,
        }

    def _extract_ticket(self, email_text: str, category: str) -> dict:
        prompt = f"""
You are analyzing a customer email categorized as "{category}".

Email:
{email_text}

Respond with ONLY a JSON object (no markdown, no commentary) in this exact shape:
{{"summary": "<one sentence summary for a support agent>", "priority": "<low|normal|high|urgent>"}}
"""
        raw = generate_response(prompt)
        parsed = self._safe_json(raw)

        return {
            "type": "create_ticket",
            "summary": (parsed.get("summary") if parsed else None) or email_text[:200],
            "priority": (parsed.get("priority") if parsed else None) or "normal",
        }

    @staticmethod
    def _safe_json(raw: str):
        """AI models often wrap JSON in ```json fences or add stray text; extract defensively."""
        if not raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return None