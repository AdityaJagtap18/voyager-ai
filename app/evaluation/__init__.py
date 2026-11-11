"""
Evaluation harness (Phase 8).

A fixed set of canned trip-planning cases, run against a real orchestrator
(LangGraph or CrewAI) and model, graded by simple structural assertions on the
result (not an LLM judge — the point is to catch real breakage: a provider
outage, a broken agent, a missing API key, not to score itinerary quality).

Builds orchestrators directly rather than importing app.api's get_workflow /
get_orchestrator caches, to avoid a circular import (api.py imports this
module to expose /api/evaluations). Mirrors api.py's own validation/resolution
logic (resolve_model/resolve_framework) at the call site instead.
"""
import time
from typing import Dict, List, Optional

from orchestration import build_orchestrator
from workflow import create_workflow

EVAL_CASES: List[Dict] = [
    {
        "id": "short-city-trip",
        "description": "A short 2-day cultural trip to a well-known city should produce attractions and a day-by-day itinerary.",
        "destination": "Rome, Italy",
        "days": 2,
        "trip_type": "cultural",
        "budget": "mid-range",
        "dietary_preferences": [],
    },
    {
        "id": "week-long-foodie-trip",
        "description": "A week-long foodie trip should produce restaurants honoring dietary preferences alongside attractions.",
        "destination": "Tokyo, Japan",
        "days": 7,
        "trip_type": "foodie",
        "budget": "premium",
        "dietary_preferences": ["vegetarian"],
    },
    {
        "id": "budget-nature-trip",
        "description": "A budget-level nature trip should still produce accommodations and an itinerary.",
        "destination": "Queenstown, New Zealand",
        "days": 4,
        "trip_type": "nature",
        "budget": "budget",
        "dietary_preferences": [],
    },
]


def _build_orchestrator(framework: str, model: Optional[str]):
    if framework == "langgraph":
        return create_workflow(model=model)
    return build_orchestrator(framework, model=model)


def _grade(case: Dict, result: Dict) -> Dict:
    """Structural pass/fail check: did planning succeed and produce non-empty
    attractions and a non-empty itinerary for the requested destination,
    without any step having silently swallowed a failure?

    research_agent.find_attractions() never raises on an LLM/provider error —
    it catches it and returns a one-item placeholder list
    (category == "error") so downstream steps have *something* to chain off
    of. That placeholder is non-empty, so a naive "attractions is non-empty"
    check alone would pass even when every agent call is failing (e.g. a bad
    API key) — this was caught live with a smoke-test key before adding the
    category=="error" check below.
    """
    if not result.get("success"):
        return {"passed": False, "reason": result.get("error", "planning failed")}

    plan = result.get("plan") or {}
    attractions = plan.get("attractions")
    if not attractions:
        return {"passed": False, "reason": "no attractions returned"}
    if any(a.get("category") == "error" for a in attractions):
        return {"passed": False, "reason": "research agent fell back to its error placeholder"}
    if not plan.get("itinerary"):
        return {"passed": False, "reason": "no itinerary returned"}

    errors = result.get("errors") or []
    if errors:
        return {"passed": False, "reason": f"agent errors: {errors}"}

    return {"passed": True, "reason": "ok"}


def run_case(case: Dict, model: Optional[str], framework: str) -> Dict:
    """Run one eval case and grade it. Never raises: an orchestrator-level
    exception (e.g. an invalid API key) is itself a failing result, not a
    crashed test run."""
    start = time.monotonic()
    try:
        orchestrator = _build_orchestrator(framework, model)
        result = orchestrator.plan_trip(
            destination=case["destination"],
            days=case["days"],
            trip_type=case["trip_type"],
            budget=case["budget"],
            dietary_preferences=case["dietary_preferences"],
        )
        grade = _grade(case, result)
    except Exception as exc:
        grade = {"passed": False, "reason": str(exc)}
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    return {
        "case_id": case["id"],
        "description": case["description"],
        "passed": grade["passed"],
        "reason": grade["reason"],
        "duration_ms": duration_ms,
    }


def run_eval_suite(model: Optional[str] = None, framework: str = "langgraph") -> List[Dict]:
    """Run every case in EVAL_CASES and return their graded results."""
    return [run_case(case, model, framework) for case in EVAL_CASES]
