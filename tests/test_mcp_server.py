"""
Tests for the MCP server (app/mcp_server.py).

mcp.tool()-decorated functions stay directly callable (confirmed against the
installed `mcp` package), so these call the tool functions as plain Python,
with app.api's route handlers mocked the same way tests/test_api.py mocks
them (get_workflow / get_orchestrator) — no real LLM calls, no stdio
transport involved.
"""
import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

pytest.importorskip("mcp")

_TMP_DB = os.path.join(tempfile.gettempdir(), "voyager_mcp_test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DB}")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.db import Base, engine  # noqa: E402
from app import mcp_server  # noqa: E402
from app import api as api_module  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_list_models_returns_plain_dicts():
    models = mcp_server.list_models()
    assert any(m["id"] == "gpt-4o-mini" for m in models)


def test_list_frameworks_returns_plain_dicts():
    frameworks = mcp_server.list_frameworks()
    assert any(f["id"] == "langgraph" and f["available"] for f in frameworks)


def test_list_agents_returns_four_agents():
    assert len(mcp_server.list_agents()) == 4


def test_plan_trip_creates_and_returns_trip(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", "sk-test")

    fake_workflow = MagicMock()
    fake_workflow.plan_trip.return_value = {
        "success": True,
        "plan": {"attractions": [{"name": "Gateway of India"}], "itinerary": {}, "restaurants": [], "accommodations": []},
        "errors": [],
    }
    monkeypatch.setattr(api_module, "get_workflow", lambda *_: fake_workflow)

    result = mcp_server.plan_trip(destination="Goa, India", days=3, trip_type="foodie")

    assert result["status"] == "complete"
    assert result["plan"]["attractions"][0]["name"] == "Gateway of India"

    fetched = mcp_server.get_trip(result["id"])
    assert fetched["destination"] == "Goa, India"

    listed = mcp_server.list_trips()
    assert len(listed) == 1


def test_plan_trip_rejects_unknown_model_with_readable_error(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", "sk-test")

    with pytest.raises(ValueError) as exc_info:
        mcp_server.plan_trip(destination="Goa, India", days=3, trip_type="foodie", model="not-a-real-model")

    assert "422" in str(exc_info.value)


def test_get_trip_raises_readable_error_for_unknown_id():
    with pytest.raises(ValueError) as exc_info:
        mcp_server.get_trip("does-not-exist")

    assert "404" in str(exc_info.value)


def test_search_knowledge_returns_empty_list_when_no_documents():
    assert mcp_server.search_knowledge("anything") == []
