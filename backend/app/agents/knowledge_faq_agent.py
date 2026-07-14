"""
agents/knowledge_faq_agent.py
----------------------------------
Knowledge Base / FAQ Agent -- the RAG knowledge base (services/knowledge_base.py)
already existed as an internal helper the Support Agent quietly leaned on
mid-conversation. This wraps it as its own standalone, sellable agent:
drop it into a website chat widget or a support form and it answers
questions directly from whatever docs the merchant uploaded, with
sources, rather than existing only as a support-agent side ingredient.

Paste -> backend/app/agents/knowledge_faq_agent.py
"""

from app.services.knowledge_base import KnowledgeBaseService
from app.ai.huggingface_client import generate_response


class KnowledgeFAQAgent:

    role_prompt = "You answer customer questions using only the provided knowledge base excerpts."

    def __init__(self):
        self.kb = KnowledgeBaseService()

    def answer(self, business_id: int, question: str, top_k: int = 3) -> dict:
        matches = self.kb.search(business_id, question, top_k=top_k)

        if not matches:
            return {
                "answer": "I don't have information on that yet -- you may want to reach out to support directly.",
                "sources": [],
                "matched": False,
            }

        context = "\n\n".join(
            f"[{m.get('title', 'Untitled')}] {m.get('text', m.get('content', ''))}" for m in matches
        )
        prompt = f"""
Answer the customer's question using ONLY the knowledge base excerpts
below. If the excerpts don't actually answer the question, say you're
not sure and suggest contacting support -- do not guess.

Knowledge base excerpts:
{context}

Customer question: {question}

Answer in 2-4 sentences, plain language, no filler.
"""
        answer_text = generate_response(prompt).strip()

        return {
            "answer": answer_text,
            "sources": [m.get("title", "Untitled") for m in matches],
            "matched": True,
        }
