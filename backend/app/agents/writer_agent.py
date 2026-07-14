"""
agents/writer_agent.py
-------------------------
Writer Agent.

Takes the specialist's brief + conversation history + reply template and
writes the actual customer-facing email. Also handles revisions when the
QA Agent kicks a draft back with issues.
"""

from app.ai.huggingface_client import generate_response


class WriterAgent:

    def write(self, subject: str, email_text: str, history_text: str, template: str, brief: dict) -> str:
        history_block = f"""
Conversation history so far (oldest to newest, for context only -- do not
repeat information the customer already has, and stay consistent with
anything already said or promised):

{history_text}
""" if history_text else ""

        prompt = f"""{brief.get('role_prompt', template)}

Internal notes from the specialist who triaged this email (for your
reference only -- do not repeat these verbatim to the customer):
{brief.get('checklist', '')}
{history_block}
Email Subject:
{subject}

Customer's latest message:
{email_text}

Write a professional, concise reply to the customer's latest message.
Take the conversation history into account so the reply feels like a natural
continuation, not a reply written in isolation. Do not include a greeting
like "Dear [Name]" -- start directly with the response body. Sign off as
"AgentHub Support Team".
"""
        return generate_response(prompt).strip()

    def revise(self, previous_draft: str, feedback: str) -> str:
        prompt = f"""
You previously wrote this customer email reply:

{previous_draft}

A quality reviewer flagged these issues:
{feedback}

Rewrite the reply, fixing every issue above. Keep the same overall structure
and sign-off ("AgentHub Support Team"), just fix the problems. Return ONLY
the corrected reply text, nothing else.
"""
        return generate_response(prompt).strip()
