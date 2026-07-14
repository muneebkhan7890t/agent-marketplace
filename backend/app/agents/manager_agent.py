"""
agents/manager_agent.py
--------------------------
Manager Agent.

Orchestrates the full pipeline:

    Classifier -> Specialist (Support/Sales/Refund) -> Writer -> QA
                -> Action Agent -> save reply

QA can send the draft back to the Writer for ONE revision if it finds
issues; after that the Manager accepts the best available draft rather than
looping forever (a human reviews everything in the dashboard regardless, so
this is a quality nudge, not a hard gate).

Every step is recorded into a trace that gets stored alongside the saved
reply (Reply.agent_trace), so a reviewer can see exactly how the pipeline
arrived at a given draft.
"""

import json

from app.services.reply_service import ReplyService
from app.services.conversation_memory import ConversationMemory
from app.services.reply_templates import ReplyTemplates

from app.agents.classifier_agent import EmailClassifierAgent
from app.agents.support_agent import SupportAgent
from app.agents.sales_agent import SalesAgent
from app.agents.refund_agent import RefundAgent
from app.agents.writer_agent import WriterAgent
from app.agents.qa_agent import QAAgent
from app.agents.action_agent import ActionAgent

MAX_QA_REVISIONS = 1


class ManagerAgent:

    def __init__(self):
        self.classifier = EmailClassifierAgent()
        self.specialists = {
            "support": SupportAgent(),
            "sales": SalesAgent(),
            "refund": RefundAgent(),
        }
        self.writer = WriterAgent()
        self.qa = QAAgent()
        self.action_agent = ActionAgent()

        self.memory = ConversationMemory()
        self.templates = ReplyTemplates()
        self.reply_service = ReplyService()

    def handle_email(
        self,
        business_id: int,
        email_id: str,
        to_email: str,
        subject: str,
        email_text: str,
        thread_id: str = None,
    ) -> dict:
        trace = {"steps": []}

        # ── 1. Classifier Agent ──────────────────────────────────────
        classification = self.classifier.classify(email_text)
        category = classification["category"]
        route = classification["route"]
        trace["steps"].append({"agent": "classifier", "category": category, "routed_to": route})

        # ── 2. Conversation memory ───────────────────────────────────
        context = self.memory.build_context(
            business_id=business_id,
            thread_id=thread_id,
            exclude_message_id=email_id,
        )
        history_text = context["history_text"]

        # ── 3. Specialist Agent ──────────────────────────────────────
        specialist = self.specialists[route]
        brief = specialist.build_brief(email_text, history_text)
        trace["steps"].append({"agent": f"{route}_specialist", "checklist": brief["checklist"]})

        template = self.templates.get_template(category)

        # ── 4. Writer Agent ──────────────────────────────────────────
        draft = self.writer.write(subject, email_text, history_text, template, brief)
        trace["steps"].append({"agent": "writer", "action": "draft", "text": draft})

        # ── 5. QA Agent (with one bounded revision loop) ─────────────
        qa_result = self.qa.review(draft, category, brief["checklist"])
        trace["steps"].append({"agent": "qa", "iteration": 1, "result": qa_result})

        revisions = 0
        while not qa_result["approved"] and revisions < MAX_QA_REVISIONS:
            revisions += 1
            feedback = "; ".join(qa_result["issues"]) or "General quality concerns."
            draft = self.writer.revise(draft, feedback)
            trace["steps"].append({"agent": "writer", "action": "revise", "text": draft})

            qa_result = self.qa.review(draft, category, brief["checklist"])
            trace["steps"].append({"agent": "qa", "iteration": revisions + 1, "result": qa_result})

        trace["qa_approved"] = qa_result["approved"]
        trace["qa_revisions"] = revisions

        # ── 6. Save the reply (always human-reviewed downstream regardless
        #        of the QA verdict -- QA improves the draft, it doesn't
        #        replace human approval) ──────────────────────────────
        saved = self.reply_service.save_reply(
            business_id=business_id,
            email_id=email_id,
            to_email=to_email,
            subject=subject,
            reply_text=draft,
            category=category,
            thread_id=thread_id,
        )
        self.reply_service.set_agent_trace(saved["reply_id"], json.dumps(trace))
        saved["agent_trace"] = trace

        # ── 7. Action Agent (refund / ticket proposals, human-approved) ─
        try:
            proposed_actions = self.action_agent.propose(
                business_id=business_id,
                reply_id=saved["reply_id"],
                email_id=email_id,
                thread_id=thread_id,
                to_email=to_email,
                subject=subject,
                email_text=email_text,
                category=category,
            )
        except Exception as exc:
            print(f"[ManagerAgent] Action Agent failed: {exc}")
            from app.error_tracking import capture_exception
            capture_exception(exc, context={"agent": "action_agent", "business_id": business_id, "email_id": email_id})
            proposed_actions = []

        saved["proposed_actions"] = proposed_actions
        return saved
