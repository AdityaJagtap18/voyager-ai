import pytest

from orchestration import (
    AGENT_CATALOG,
    FRAMEWORK_REGISTRY,
    DEFAULT_FRAMEWORK,
    build_orchestrator,
    is_available,
    resolve_framework,
)


def test_langgraph_is_always_available():
    assert FRAMEWORK_REGISTRY["langgraph"].available is True
    assert is_available("langgraph") is True


def test_resolve_framework_prefers_explicit_known_id():
    assert resolve_framework("crewai") == "crewai"


def test_resolve_framework_falls_back_to_default_for_unknown_id():
    assert resolve_framework("not-a-real-framework") == DEFAULT_FRAMEWORK


def test_resolve_framework_falls_back_to_default_when_none_given():
    assert resolve_framework(None) == DEFAULT_FRAMEWORK


def test_is_available_false_for_unknown_framework():
    assert is_available("not-a-real-framework") is False


def test_build_orchestrator_rejects_langgraph():
    # langgraph is handled by app.api.get_workflow's existing cache, not this factory.
    with pytest.raises(ValueError):
        build_orchestrator("langgraph")


def test_agent_catalog_entries_have_required_fields():
    assert len(AGENT_CATALOG) == 4
    for agent in AGENT_CATALOG:
        assert agent["id"]
        assert agent["name"]
        assert agent["role"]
        assert agent["goal"]
        assert agent["data_source"]


def test_itinerary_agent_catalog_entry_flags_deterministic_source():
    itinerary = next(a for a in AGENT_CATALOG if a["id"] == "itinerary")
    assert "Deterministic" in itinerary["data_source"]
