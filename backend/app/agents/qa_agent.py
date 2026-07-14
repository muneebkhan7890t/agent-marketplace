"""
agents/qa_agent.py
---------------------
QA Agent.

Reviews the Writer's draft before it's shown to a human for approval.
Checks for the failure modes that matter most in an auto-reply system:
made-up facts/promises, wrong tone, confirming a refund/action that hasn't
actually been approved, and unprofessional or overly long replies.

Returns a structured verdict; the Manager Agent uses this to decide whether
to send the draft on as-is or ask the Writer Agent for one revision.
"""

import json
import re

from app.ai.huggingface_client import generate_response

MAX_REPLY_CHARS = 3000


class QAAgent:

    def review(self, draft: str, category: str, checklist: str) -> dict:
        # Cheap deterministic checks first -- no need to spend an AI call on these.
        hard_issues = []
        if not draft or not draft.strip():
            hard_issues.append("The draft is empty.")
        if len(draft) > MAX_REPLY_CHARS:
            hard_issues.append("The draft is far too long for a support email.")
        if category.strip().lower() == "refund" and re.search(
            r"\b(refund (has been|is) (issued|processed|approved)|we have refunded)\b",
            draft, re.IGNORECASE,
        ):
            hard_issues.append(
                "The draft states the refund has already been issued/approved, "
                "but that decision is made separately by a human reviewer -- "
                "it must not be confirmed as done in the email."
            )

        if hard_issues:
            return {"approved": False, "issues": hard_issues}

        prompt = f"""
You are a quality-assurance reviewer for customer support emails.

Specialist's internal notes (what the reply was supposed to address):
{checklist}

Draft reply to review:
{draft}

Respond with ONLY a JSON object (no markdown, no commentary) in this exact shape:
{{"approved": true or false, "issues": ["<issue 1>", "<issue 2>", ...]}}

Mark approved=false if the draft: ignores something in the specialist's
notes, makes up specific facts/policies/prices that weren't given, promises
something the company may not be able to deliver, or reads as rude,
robotic, or unprofessional. Otherwise mark approved=true with an empty
issues list.
"""
        raw = generate_response(prompt)
        parsed = self._safe_json(raw)

        if not parsed or "approved" not in parsed:
            # If the QA model itself misbehaves, fail open to "approved" --
            # we'd rather show a human a decent draft than block the pipeline.
            return {"approved": True, "issues": []}

        return {
            "approved": bool(parsed.get("approved")),
            "issues": parsed.get("issues") or [],
        }

    @staticmethod
    def _safe_json(raw: str):
        if not raw:
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            return None
