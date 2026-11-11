"""
Orchestration framework registry (Phase 6).

Before this, the only way to run the four-agent travel pipeline was
app/workflow.py's LangGraph StateGraph. This package adds a second,
interchangeable orchestration engine (CrewAI, see crewai_adapter.py) that
drives the exact same agent objects — same prompts, same JSON contracts,
same real ORS geocoding in the itinerary step — through a different
framework's own Agent/Task/Crew primitives, to demonstrate that the
business logic isn't tied to LangGraph.

Mirrors app/llm_gateway.py's pattern: a small registry with an
`available`/`configured`-style flag, a resolver with a sane fallback, and a
factory. langgraph is always available (it's a hard dependency already).
crewai is optional — only installed if you want to try it — so availability
is a live `try: import crewai` check, not an assumption.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class FrameworkInfo:
    id: str
    label: str
    description: str
    available: bool


def _crewai_available() -> bool:
    try:
        import crewai  # noqa: F401
    except ImportError:
        return False
    return True


FRAMEWORK_REGISTRY: Dict[str, FrameworkInfo] = {
    "langgraph": FrameworkInfo(
        id="langgraph",
        label="LangGraph",
        description="The original orchestration engine: a StateGraph that runs the four agents in a fixed sequence.",
        available=True,
    ),
    "crewai": FrameworkInfo(
        id="crewai",
        label="CrewAI",
        description="Runs the same four agents as a CrewAI Crew (Agent/Task/Process.sequential) instead of a LangGraph StateGraph.",
        available=_crewai_available(),
    ),
}

DEFAULT_FRAMEWORK = "langgraph"

# Static roster for the Agent Studio UI — describes the four agents that both
# orchestration frameworks above drive unchanged. "data_source" distinguishes
# the LLM-generated steps from the itinerary step's real geocoding/routing,
# since that distinction matters for Phase 6 (an LLM-driven CrewAI agent still
# calls into the same deterministic code for scheduling, never re-invents it).
AGENT_CATALOG = [
    {
        "id": "research",
        "name": "Research Agent",
        "role": "Attraction Discovery",
        "goal": "Find attractions that match the destination and trip type",
        "data_source": "LLM-generated",
    },
    {
        "id": "accommodation",
        "name": "Accommodation Agent",
        "role": "Lodging Scout",
        "goal": "Recommend hotels near the researched attractions",
        "data_source": "LLM-generated, ranked by real ORS distance to attractions",
    },
    {
        "id": "dining",
        "name": "Dining Agent",
        "role": "Restaurant Scout",
        "goal": "Recommend restaurants honoring dietary preferences, near the accommodation",
        "data_source": "LLM-generated, ranked by real ORS distance",
    },
    {
        "id": "itinerary",
        "name": "Itinerary Agent",
        "role": "Scheduler & Router",
        "goal": "Build a realistic day-by-day schedule with meals integrated",
        "data_source": "Deterministic — real OpenRouteService geocoding, distance matrices, and route optimization (not LLM-generated)",
    },
]


def resolve_framework(framework_id: Optional[str]) -> str:
    """Pick the framework to actually use: the requested one if known, else the default."""
    if framework_id and framework_id in FRAMEWORK_REGISTRY:
        return framework_id
    return DEFAULT_FRAMEWORK


def is_available(framework_id: str) -> bool:
    info = FRAMEWORK_REGISTRY.get(framework_id)
    return bool(info and info.available)


def build_orchestrator(framework_id: str, model: Optional[str] = None):
    """Construct a fresh orchestrator for the given framework id.

    Returns an object exposing the same `plan_trip(destination, days,
    trip_type, budget, dietary_preferences) -> dict` contract as
    app.workflow.MultiAgentWorkflow, so callers don't need to care which
    framework they got. langgraph's case is handled by the caller (app/api.py
    already has a cached `get_workflow` for it); this factory only needs to
    cover the non-default frameworks.
    """
    if framework_id == "crewai":
        from orchestration.crewai_adapter import CrewAIOrchestrator

        return CrewAIOrchestrator(model=model)
    raise ValueError(f"No orchestrator factory for framework '{framework_id}'")
