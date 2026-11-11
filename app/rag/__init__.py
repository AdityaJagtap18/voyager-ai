"""
RAG knowledge base (Phase 7).

Lets anyone add free-text notes/guides about a destination (a packing list,
visa rules, a local's tips — whatever isn't already covered by the agents'
own LLM knowledge) and retrieves the most relevant passages for a query by
embedding-similarity search. No vector database — chunk embeddings are
stored as a JSON column on KnowledgeChunk (app/models_db.py) and compared
with plain cosine similarity in Python, which is plenty fast at the scale a
single traveler's notes will ever reach, and avoids pulling in a vector-store
dependency for what's a handful of rows.

This module is bare-imported (consistent with llm_gateway/orchestration) from
workflow.py and crewai_adapter.py so the research step can ground itself in
any matching notes — but it also needs `app.db`/`app.models_db`, which are
only ever package-style imported elsewhere (api.py, models_db.py itself), so
unlike config/llm_gateway there's no import-identity risk in reusing that
style here. The one thing this module can't assume is that the repo root is
already on sys.path when some *other* module bare-imports it first, so it
adds the repo root itself, defensively, the same way api.py adds app/.
"""
import math
import os
import sys
from typing import Dict, List, Optional, Tuple

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_APP_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models_db import KnowledgeChunk, KnowledgeDocument  # noqa: E402
from rag.chunking import chunk_text  # noqa: E402
from rag.embeddings import EmbeddingUnavailableError, embed_text, embed_texts  # noqa: E402

__all__ = [
    "EmbeddingUnavailableError",
    "ingest_document",
    "list_documents",
    "search_knowledge",
    "get_context_for_destination",
]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _db_scope(db: Optional[Session]):
    """Use the given session if provided, else open and close a short-lived one."""
    if db is not None:
        return db, False
    return SessionLocal(), True


def ingest_document(destination: str, title: str, content: str, db: Optional[Session] = None) -> Tuple[KnowledgeDocument, int]:
    """Chunk, embed, and store a document. Returns (document, chunk_count).

    Embeds before writing anything, so a failed embedding call (e.g. no
    OPENAI_API_KEY) never leaves an orphaned document with zero chunks behind
    — either the whole document is stored with all its chunks, or nothing is.
    """
    chunks = chunk_text(content)
    embeddings = embed_texts(chunks) if chunks else []

    session, owns_session = _db_scope(db)
    try:
        document = KnowledgeDocument(destination=destination, title=title, content=content)
        session.add(document)
        session.commit()
        session.refresh(document)

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            session.add(KnowledgeChunk(document_id=document.id, chunk_index=idx, text=chunk, embedding=embedding))
        if chunks:
            session.commit()

        return document, len(chunks)
    finally:
        if owns_session:
            session.close()


def list_documents(db: Optional[Session] = None) -> List[Dict]:
    session, owns_session = _db_scope(db)
    try:
        documents = session.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()
        results = []
        for doc in documents:
            chunk_count = session.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc.id).count()
            results.append(
                {
                    "id": doc.id,
                    "destination": doc.destination,
                    "title": doc.title,
                    "chunk_count": chunk_count,
                    "created_at": doc.created_at,
                }
            )
        return results
    finally:
        if owns_session:
            session.close()


def search_knowledge(
    query: str, destination: Optional[str] = None, top_k: int = 5, db: Optional[Session] = None
) -> List[Dict]:
    """Embed `query` and return the top_k most similar chunks, optionally
    filtered to one destination (case-insensitive exact match)."""
    session, owns_session = _db_scope(db)
    try:
        chunk_query = session.query(KnowledgeChunk, KnowledgeDocument).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        )
        if destination:
            chunk_query = chunk_query.filter(KnowledgeDocument.destination.ilike(destination))
        rows = chunk_query.all()
        if not rows:
            return []

        query_embedding = embed_text(query)
        scored = [
            {
                "document_id": chunk.document_id,
                "document_title": document.title,
                "destination": document.destination,
                "chunk_text": chunk.text,
                "score": _cosine_similarity(query_embedding, chunk.embedding),
            }
            for chunk, document in rows
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]
    finally:
        if owns_session:
            session.close()


def get_context_for_destination(destination: str, max_chars: int = 1200, top_k: int = 3) -> str:
    """Convenience wrapper for the agents: a ready-to-use context string of
    the top matching chunks for a destination, or "" if there's nothing to
    retrieve or embeddings aren't configured.

    Checks whether any chunks exist for this destination before embedding
    anything — planning a trip for a destination with no knowledge base
    entries (true for every destination by default) costs zero extra API
    calls, not a wasted embedding request per trip.
    """
    session, owns_session = _db_scope(None)
    try:
        has_chunks = (
            session.query(KnowledgeChunk)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .filter(KnowledgeDocument.destination.ilike(destination))
            .first()
            is not None
        )
        if not has_chunks:
            return ""

        try:
            results = search_knowledge(destination, destination=destination, top_k=top_k, db=session)
        except EmbeddingUnavailableError:
            return ""

        context = ""
        for result in results:
            addition = f"- {result['chunk_text']}\n"
            if len(context) + len(addition) > max_chars:
                break
            context += addition
        return context.strip()
    finally:
        if owns_session:
            session.close()
