"""Tests for trip document storage (app/documents.py, Phase 4 remaining scope)."""
import os
import shutil
import tempfile

import pytest

import documents


@pytest.fixture(autouse=True)
def _isolated_documents_dir(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    monkeypatch.setattr(documents, "DOCUMENTS_DIR", tmp_dir)
    yield
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_save_document_bytes_writes_file_and_returns_metadata():
    meta = documents.save_document_bytes("trip-1", "ticket.pdf", b"fake pdf bytes")
    assert meta["filename"] == "ticket.pdf"
    assert meta["content_type"] == "application/pdf"
    assert meta["size_bytes"] == len(b"fake pdf bytes")
    assert os.path.exists(meta["stored_path"])
    with open(meta["stored_path"], "rb") as f:
        assert f.read() == b"fake pdf bytes"


def test_save_document_bytes_strips_directory_components_from_filename():
    meta = documents.save_document_bytes("trip-1", "../../etc/passwd", b"data")
    assert meta["filename"] == "passwd"
    assert os.path.dirname(meta["stored_path"]) == os.path.join(documents.DOCUMENTS_DIR, "trip-1")


def test_save_document_bytes_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(documents, "MAX_DOCUMENT_BYTES", 5)
    with pytest.raises(documents.DocumentTooLargeError):
        documents.save_document_bytes("trip-1", "big.txt", b"too big for the limit")


def test_delete_document_file_removes_existing_file():
    meta = documents.save_document_bytes("trip-1", "note.txt", b"hello")
    documents.delete_document_file(meta["stored_path"])
    assert not os.path.exists(meta["stored_path"])


def test_delete_document_file_is_a_noop_for_missing_file():
    documents.delete_document_file(os.path.join(documents.DOCUMENTS_DIR, "does-not-exist.txt"))
