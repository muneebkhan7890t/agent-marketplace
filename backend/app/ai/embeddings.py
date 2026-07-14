"""
ai/embeddings.py
----------------
Turns text into a vector so we can compare "how similar" two pieces of text
are (cosine similarity) -- the core operation behind RAG retrieval.

Two backends, picked automatically:

1. "sentence-transformers" (preferred) -- a real local semantic embedding
   model (all-MiniLM-L6-v2). Much better retrieval quality. Free and runs
   on CPU, no per-call API cost -- just needs one pip install:
       pip install sentence-transformers

2. "hashing" (automatic fallback, zero extra dependencies) -- a classic
   "feature hashing" bag-of-words vectorizer. Not true semantic
   understanding, but it's deterministic, free, dependency-free, and good
   enough to retrieve the right FAQ/policy chunk for an MVP.

Whichever backend produced a stored embedding is recorded alongside it
(see models/knowledge.py: embedding_backend), so if you later install
sentence-transformers, old hashing-based embeddings are recognized as
stale rather than silently compared against incompatible vectors. Use the
`/knowledge/reindex` endpoint to re-embed existing documents after
upgrading the backend.
"""

import hashlib
import json
import math
import re
from collections import Counter

HASHING_DIM = 256

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "but", "with", "at", "by",
    "from", "as", "it", "this", "that", "these", "those", "i", "you", "we",
    "they", "he", "she", "your", "our", "my", "their", "will", "would",
    "can", "could", "should", "do", "does", "did", "have", "has", "had",
}

# ------------------------------------------------------------------ #
# Backend detection
# ------------------------------------------------------------------ #

try:
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    BACKEND = "sentence-transformers"
except Exception:
    _model = None
    BACKEND = "hashing"


# ------------------------------------------------------------------ #
# Hashing fallback
# ------------------------------------------------------------------ #

def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def _hash_embed(text: str) -> list[float]:
    tokens = _tokenize(text)
    vector = [0.0] * HASHING_DIM

    if not tokens:
        return vector

    counts = Counter(tokens)
    for token, count in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        index = int(digest, 16) % HASHING_DIM
        sign = 1.0 if int(digest, 16) % 2 == 0 else -1.0
        # log-dampen term frequency so one repeated word doesn't dominate
        vector[index] += sign * (1.0 + math.log(count))

    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def embed_text(text: str) -> list[float]:
    """Return an embedding vector for a single piece of text."""
    text = (text or "").strip()
    if not text:
        return [0.0] * (384 if BACKEND == "sentence-transformers" else HASHING_DIM)

    if _model is not None:
        return _model.encode(text, normalize_embeddings=True).tolist()

    return _hash_embed(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch version -- faster with sentence-transformers, same result otherwise."""
    if _model is not None:
        return _model.encode(texts, normalize_embeddings=True).tolist()
    return [_hash_embed(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Both embed_text()/embed_texts() outputs are already L2-normalized,
    so a plain dot product IS the cosine similarity."""
    if len(a) != len(b):
        return -1.0  # incompatible backends/dimensions -- never treat as a match
    return sum(x * y for x, y in zip(a, b))


def serialize(vector: list[float]) -> str:
    return json.dumps(vector)


def deserialize(raw: str) -> list[float]:
    return json.loads(raw)
