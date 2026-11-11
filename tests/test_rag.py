"""
Tests for the RAG knowledge base (app/rag).

Uses its own isolated in-memory SQLite engine/session (not app.db's global
one) passed explicitly via each function's `db` parameter, so these tests
don't depend on which other test file happened to configure app.db's
DATABASE_URL first. embed_texts/embed_text are mocked throughout — no network
calls, no OPENAI_API_KEY needed.
"""
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import rag as rag_module
from app.db import Base
from rag.chunking import chunk_text


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _fake_embedding(seed: float, dims: int = 4):
    return [seed, 1 - seed, 0.0, 0.0]


def test_chunk_text_splits_long_text_with_overlap():
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=150)
    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)


def test_chunk_text_returns_single_chunk_for_short_text():
    assert chunk_text("short note") == ["short note"]


def test_chunk_text_returns_empty_list_for_blank_text():
    assert chunk_text("   ") == []


def test_ingest_document_stores_document_and_embedded_chunks(db_session):
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.9)]):
        document, chunk_count = rag_module.ingest_document(
            "Goa, India", "Local tips", "Carry cash, many beach shacks don't take cards.", db=db_session
        )

    assert chunk_count == 1
    assert document.destination == "Goa, India"

    docs = rag_module.list_documents(db=db_session)
    assert len(docs) == 1
    assert docs[0]["chunk_count"] == 1


def test_search_knowledge_ranks_by_similarity(db_session):
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.9)]):
        rag_module.ingest_document("Goa, India", "Beach tips", "Beach shacks are cash-only.", db=db_session)
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.1)]):
        rag_module.ingest_document("Goa, India", "Visa info", "E-visa takes 3 business days.", db=db_session)

    with patch("rag.embed_text", return_value=_fake_embedding(0.95)):
        results = rag_module.search_knowledge("cash payments", destination="Goa, India", top_k=2, db=db_session)

    assert len(results) == 2
    assert results[0]["document_title"] == "Beach tips"
    assert results[0]["score"] > results[1]["score"]


def test_search_knowledge_filters_by_destination(db_session):
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.5)]):
        rag_module.ingest_document("Goa, India", "Goa note", "Some Goa content.", db=db_session)
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.5)]):
        rag_module.ingest_document("Paris, France", "Paris note", "Some Paris content.", db=db_session)

    with patch("rag.embed_text", return_value=_fake_embedding(0.5)):
        results = rag_module.search_knowledge("anything", destination="Paris, France", db=db_session)

    assert len(results) == 1
    assert results[0]["destination"] == "Paris, France"


def test_search_knowledge_returns_empty_when_no_documents(db_session):
    with patch("rag.embed_text", return_value=_fake_embedding(0.5)):
        assert rag_module.search_knowledge("anything", db=db_session) == []


def test_get_context_for_destination_skips_embedding_when_no_chunks_exist(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(rag_module, "SessionLocal", SessionLocal)

    with patch("rag.embed_text") as mock_embed:
        context = rag_module.get_context_for_destination("Nowhere, Nowhere")

    assert context == ""
    mock_embed.assert_not_called()


def test_get_context_for_destination_returns_formatted_context(monkeypatch):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(rag_module, "SessionLocal", SessionLocal)

    seed_session = SessionLocal()
    with patch("rag.embed_texts", return_value=[_fake_embedding(0.8)]):
        rag_module.ingest_document("Goa, India", "Local tips", "Carry cash for beach shacks.", db=seed_session)
    seed_session.close()

    with patch("rag.embed_text", return_value=_fake_embedding(0.8)):
        context = rag_module.get_context_for_destination("Goa, India")

    assert "Carry cash for beach shacks." in context
