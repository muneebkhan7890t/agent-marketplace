"""
models/knowledge.py
--------------------
Stores the business's knowledge base as embedded chunks, used for
Retrieval-Augmented Generation (RAG) when writing email replies.

A single uploaded document (FAQ page, policy doc, product sheet, etc.) is
split into several rows here -- one per chunk -- each with its own
embedding vector so we can retrieve just the relevant paragraph(s) instead
of stuffing the whole document into every prompt.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

from app.database import Base


class KnowledgeChunk(Base):

    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, index=True)

    title = Column(String, index=True)        # source document name, e.g. "Refund Policy"

    chunk_index = Column(Integer)              # position of this chunk within the source doc

    content = Column(Text)                     # the actual chunk text

    embedding = Column(Text)                   # JSON-encoded vector, e.g. "[0.01, -0.22, ...]"

    embedding_backend = Column(String)         # which embedder produced the vector (see ai/embeddings.py)

    created_at = Column(DateTime, default=datetime.utcnow)
