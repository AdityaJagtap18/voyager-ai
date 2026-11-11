"""Tests for the evaluation harness (app/evaluation, Phase 8)."""
from unittest.mock import MagicMock, patch

from evaluation import EVAL_CASES, run_case, run_eval_suite


def _case():
    return EVAL_CASES[0]


def test_run_case_passes_on_a_well_formed_result():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {
        "success": True,
        "plan": {"attractions": [{"name": "x"}], "itinerary": {"itinerary": [{"day": 1}]}},
        "errors": [],
    }
    with patch("evaluation.create_workflow", return_value=orchestrator):
        result = run_case(_case(), model=None, framework="langgraph")

    assert result["passed"] is True
    assert result["case_id"] == _case()["id"]
    assert isinstance(result["duration_ms"], float)


def test_run_case_fails_when_plan_trip_raises():
    orchestrator = MagicMock()
    orchestrator.plan_trip.side_effect = RuntimeError("AuthenticationError: invalid key")
    with patch("evaluation.create_workflow", return_value=orchestrator):
        result = run_case(_case(), model=None, framework="langgraph")

    assert result["passed"] is False
    assert "AuthenticationError" in result["reason"]


def test_run_case_fails_when_attractions_or_itinerary_missing():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {
        "success": True,
        "plan": {"attractions": [], "itinerary": {}},
        "errors": [],
    }
    with patch("evaluation.create_workflow", return_value=orchestrator):
        result = run_case(_case(), model=None, framework="langgraph")

    assert result["passed"] is False
    assert "attractions" in result["reason"]


def test_run_case_fails_when_research_agent_fell_back_to_error_placeholder():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {
        "success": True,
        "plan": {
            "attractions": [{"name": "Error occurred", "category": "error"}],
            "itinerary": {"itinerary": [{"day": 1}]},
        },
        "errors": [],
    }
    with patch("evaluation.create_workflow", return_value=orchestrator):
        result = run_case(_case(), model=None, framework="langgraph")

    assert result["passed"] is False
    assert "error placeholder" in result["reason"]


def test_run_case_fails_when_success_false():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {"success": False, "error": "provider outage"}
    with patch("evaluation.create_workflow", return_value=orchestrator):
        result = run_case(_case(), model=None, framework="langgraph")

    assert result["passed"] is False
    assert result["reason"] == "provider outage"


def test_run_eval_suite_runs_every_case():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {
        "success": True,
        "plan": {"attractions": [{"name": "x"}], "itinerary": {"itinerary": [{"day": 1}]}},
        "errors": [],
    }
    with patch("evaluation.create_workflow", return_value=orchestrator):
        results = run_eval_suite(model=None, framework="langgraph")

    assert len(results) == len(EVAL_CASES)
    assert all(r["passed"] for r in results)


def test_run_eval_suite_uses_build_orchestrator_for_non_langgraph_framework():
    orchestrator = MagicMock()
    orchestrator.plan_trip.return_value = {
        "success": True,
        "plan": {"attractions": [{"name": "x"}], "itinerary": {"itinerary": [{"day": 1}]}},
        "errors": [],
    }
    with patch("evaluation.build_orchestrator", return_value=orchestrator) as mock_build:
        results = run_eval_suite(model="gpt-4o-mini", framework="crewai")

    assert mock_build.call_count == len(EVAL_CASES)
    mock_build.assert_called_with("crewai", model="gpt-4o-mini")
    assert all(r["passed"] for r in results)
