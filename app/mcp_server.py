"""
Voyager AI — MCP server (Phase 7).

Exposes the same trip-planning capability as the FastAPI backend
(app/api.py), but over the Model Context Protocol so an MCP client (Claude
Desktop, another agent) can plan and inspect trips as tool calls instead of
HTTP requests. This reuses app/api.py's route handlers directly as plain
Python functions — they're ordinary functions underneath FastAPI's
decorators, so calling them here with a manually-opened DB session (instead
of through FastAPI's Depends(get_db)) runs the exact same validation,
orchestration, and persistence code the HTTP API uses. No separate
trip-creation logic to keep in sync.

Run with:
    python app/mcp_server.py
and point an MCP client (e.g. Claude Desktop's config) at this command with
stdio transport.
"""
import os
import sys
from typing import List, Optional

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from fastapi import HTTPException  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

from app import api as api_module  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.schemas import TripCreateRequest  # noqa: E402


def _reraise_as_value_error(exc: HTTPException):
    """app/api.py's route handlers raise FastAPI's HTTPException for 404/422/503 —
    translate that into a plain exception an MCP client can render sensibly,
    since HTTPException's own string form is a Starlette implementation detail."""
    raise ValueError(f"{exc.status_code}: {exc.detail}") from exc

mcp = FastMCP(
    "voyager-ai",
    instructions=(
        "Plan multi-day trips with Voyager AI's four-agent travel workflow "
        "(research, accommodation, dining, itinerary). Use list_models and "
        "list_frameworks to see what's configured before calling plan_trip."
    ),
)


@mcp.tool()
def list_models() -> list:
    """List the chat models the server can route to and whether each is configured."""
    return [m.model_dump() for m in api_module.list_models()]


@mcp.tool()
def list_frameworks() -> list:
    """List the orchestration frameworks (LangGraph, CrewAI) and whether each is installed."""
    return [f.model_dump() for f in api_module.list_frameworks()]


@mcp.tool()
def list_agents() -> list:
    """List the four agents in the travel-planning pipeline and what each does."""
    return [a.model_dump() for a in api_module.list_agents()]


@mcp.tool()
def plan_trip(
    destination: str,
    days: int,
    trip_type: str,
    budget: str = "mid-range",
    dietary_preferences: Optional[List[str]] = None,
    model: Optional[str] = None,
    framework: Optional[str] = None,
) -> dict:
    """Plan a new trip. trip_type: historic/adventure/relaxation/foodie/cultural/romantic/nature.
    budget: budget/mid-range/premium. model/framework: ids from list_models/list_frameworks, or
    omit both for the server's defaults."""
    db = SessionLocal()
    try:
        payload = TripCreateRequest(
            destination=destination,
            days=days,
            trip_type=trip_type,
            budget=budget,
            dietary_preferences=dietary_preferences or [],
            model=model,
            framework=framework,
        )
        try:
            trip = api_module.create_trip(payload, db=db)
        except HTTPException as exc:
            _reraise_as_value_error(exc)
        return api_module.TripDetail.model_validate(trip).model_dump()
    finally:
        db.close()


@mcp.tool()
def get_trip(trip_id: str) -> dict:
    """Fetch a previously planned trip by id."""
    db = SessionLocal()
    try:
        try:
            trip = api_module.get_trip(trip_id, db=db)
        except HTTPException as exc:
            _reraise_as_value_error(exc)
        return api_module.TripDetail.model_validate(trip).model_dump()
    finally:
        db.close()


@mcp.tool()
def list_trips() -> list:
    """List all planned trips, most recent first."""
    db = SessionLocal()
    try:
        trips = api_module.list_trips(db=db)
        return [api_module.TripSummary.model_validate(t).model_dump() for t in trips]
    finally:
        db.close()


@mcp.tool()
def search_knowledge(query: str, destination: Optional[str] = None, top_k: int = 5) -> list:
    """Search the RAG knowledge base (traveler notes/guides) for passages matching a query,
    optionally scoped to one destination."""
    db = SessionLocal()
    try:
        results = api_module.search_knowledge_documents(query, destination=destination, top_k=top_k, db=db)
        return [r.model_dump() for r in results]
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    mcp.run()
