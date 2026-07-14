"""
services/knowledge_base.py
---------------------------
The RAG layer: turns a business's raw documents (FAQs, refund policy,
shipping policy, product info, etc.) into searchable chunks, and answers
"what's relevant to this customer question?" at reply time.

Flow:
  add_document()  -> chunk text -> embed each chunk -> store in DB
  search(query)   -> embed query -> cosine similarity vs stored chunks
                     -> top-k most relevant chunks, above a relevance floor
"""

from datetime import datetime

from app.database import SessionLocal
from app.models.knowledge import KnowledgeChunk
from app.ai.embeddings import (
    embed_text,
    embed_texts,
    cosine_similarity,
    serialize,
    deserialize,
    BACKEND,
)

CHUNK_SIZE = 800       # characters per chunk
CHUNK_OVERLAP = 120    # overlap so we don't cut a fact in half at a boundary
MIN_RELEVANCE = 0.15   # below this cosine score, a chunk isn't worth injecting


class KnowledgeBaseService:

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #

    def _chunk_text(self, text: str) -> list[str]:
        """Simple sliding-window chunker on whitespace-normalized text."""
        text = " ".join(text.split())
        if not text:
            return []

        if len(text) <= CHUNK_SIZE:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP
        return chunks

    def add_document(self, business_id: int, title: str, content: str) -> dict:
        """
        Chunk + embed + store a document. Re-uploading a document with the
        same title replaces the old chunks (so editing a policy doc is just
        "upload again").
        """
        chunks = self._chunk_text(content)
        if not chunks:
            return {"title": title, "chunks_created": 0, "error": "Document was empty"}

        vectors = embed_texts(chunks)

        db = SessionLocal()
        try:
            # Replace any existing version of this document
            db.query(KnowledgeChunk).filter(
                KnowledgeChunk.business_id == business_id,
                KnowledgeChunk.title == title,
            ).delete()

            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                db.add(KnowledgeChunk(
                    business_id=business_id,
                    title=title,
                    chunk_index=i,
                    content=chunk,
                    embedding=serialize(vector),
                    embedding_backend=BACKEND,
                    created_at=datetime.utcnow(),
                ))
            db.commit()

            return {"title": title, "chunks_created": len(chunks), "backend": BACKEND}
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # Management
    # ------------------------------------------------------------------ #

    def list_documents(self, business_id: int) -> list[dict]:
        """One row per source document, not per chunk."""
        db = SessionLocal()
        try:
            rows = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.business_id == business_id
            ).order_by(KnowledgeChunk.title, KnowledgeChunk.chunk_index).all()

            docs = {}
            for r in rows:
                if r.title not in docs:
                    docs[r.title] = {"title": r.title, "chunks": 0, "created_at": str(r.created_at)}
                docs[r.title]["chunks"] += 1
            return list(docs.values())
        finally:
            db.close()

    def delete_document(self, business_id: int, title: str) -> dict:
        db = SessionLocal()
        try:
            deleted = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.business_id == business_id,
                KnowledgeChunk.title == title,
            ).delete()
            db.commit()
            return {"title": title, "chunks_deleted": deleted}
        finally:
            db.close()

    def reindex(self, business_id: int) -> dict:
        """
        Re-embed every existing chunk with whichever backend is active now.
        Run this once after installing sentence-transformers so old
        hashing-based embeddings get upgraded to real semantic embeddings.
        """
        db = SessionLocal()
        try:
            rows = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.business_id == business_id
            ).all()
            for r in rows:
                r.embedding = serialize(embed_text(r.content))
                r.embedding_backend = BACKEND
            db.commit()
            return {"chunks_reindexed": len(rows), "backend": BACKEND}
        finally:
            db.close()

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    def search(self, business_id: int, query: str, top_k: int = 3) -> list[dict]:
        """
        Return the top_k most relevant chunks for `query`, each with its
        source title and similarity score. Chunks embedded with a different
        backend than the one currently active are skipped (call reindex()
        first) rather than compared incorrectly.
        """
        query_vector = embed_text(query)

        db = SessionLocal()
        try:
            rows = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.business_id == business_id,
                KnowledgeChunk.embedding_backend == BACKEND,
            ).all()
        finally:
            db.close()

        if not rows:
            return []

        scored = []
        for r in rows:
            try:
                vector = deserialize(r.embedding)
            except Exception:
                continue
            score = cosine_similarity(query_vector, vector)
            if score >= MIN_RELEVANCE:
                scored.append({"title": r.title, "content": r.content, "score": round(score, 4)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
