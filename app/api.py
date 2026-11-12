"""
Voyager AI — FastAPI backend (Phase 2).

Wraps the existing LangGraph multi-agent workflow (app/workflow.py) behind a
REST API and persists trips to a database (SQLite by default, Postgres via
DATABASE_URL — see app/db.py). The agents themselves are untouched.

Run with:
    uvicorn app.api:app --reload
"""
import os
import secrets
import sys
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

# Mirror streamlit_app.py's sys.path setup: the agent modules (workflow.py and
# everything it imports) use bare imports like `from config import Config`,
# which only resolve if app/ itself is on sys.path, not just the repo root.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from app.db import get_db, init_db  # noqa: E402
from app.models_db import Booking as BookingModel  # noqa: E402
from app.models_db import Expense as ExpenseModel  # noqa: E402
from app.models_db import Trip  # noqa: E402

# Bare imports (not `app.config`/`app.llm_gateway`): the agent modules these
# transitively construct (via app.workflow -> agents.* -> llm_gateway -> config)
# all resolve `config`/`llm_gateway` as bare top-level modules once app/ is on
# sys.path (see the sys.path.insert above) — importing them the same way here
# means api.py shares the *same* Config/registry objects the agents see,
# instead of a second copy with its own independently-loaded state, which
# would make monkeypatching Config in tests silently not apply.
from config import Config  # noqa: E402
from llm_gateway import MODEL_REGISTRY, is_configured, resolve_model  # noqa: E402
from orchestration import (  # noqa: E402
    AGENT_CATALOG,
    FRAMEWORK_REGISTRY,
    build_orchestrator,
    is_available as is_framework_available,
    resolve_framework,
)
from rag import EmbeddingUnavailableError, ingest_document, list_documents, search_knowledge  # noqa: E402
from evaluation import EVAL_CASES, run_eval_suite  # noqa: E402
from guardrails import is_blocked, scan_text  # noqa: E402
from documents import DocumentTooLargeError, delete_document_file, save_document_bytes  # noqa: E402
from services import currency_api, flights_api, hotels_api, ors_api, weather_api  # noqa: E402
from services.flights_api import FlightsAPIError  # noqa: E402
from services.hotels_api import HotelsAPIError  # noqa: E402
from services.ors_api import ORSError  # noqa: E402
from services.weather_api import WeatherAPIError  # noqa: E402
from app.models_db import EvaluationRun, GuardrailEvent, TripDocument  # noqa: E402
from app.schemas import (  # noqa: E402
    BOOKING_STATUSES,
    BOOKING_TYPES,
    BUDGET_LEVELS,
    EXPENSE_CATEGORIES,
    TRIP_TYPES,
    AgentInfoResponse,
    Booking,
    BookingCreateRequest,
    BookingStatusUpdate,
    EvaluationRunDetail,
    EvaluationRunRequest,
    EvaluationRunSummary,
    CurrencyConversion,
    CurrencyRates,
    Expense,
    ExpenseCreateRequest,
    FlightOffer,
    FrameworkInfoResponse,
    GuardrailEventSummary,
    HotelOffer,
    GuardrailScanRequest,
    GuardrailScanResult,
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentSummary,
    KnowledgeSearchResult,
    ModelInfoResponse,
    PlaceResult,
    PublicTripView,
    RouteResponse,
    SelectIndexRequest,
    ShareLinkResponse,
    TravelBudgetCapsUpdate,
    TripBudgetUpdate,
    TripCreateRequest,
    TripDetail,
    TripDocumentSummary,
    TripSummary,
    WeatherForecastResponse,
)
from app.workflow import MultiAgentWorkflow, create_workflow  # noqa: E402
from agents.itinerary_agent import ItineraryAgent  # noqa: E402
from services.budget_allocator import allocate_budget  # noqa: E402
from services.flight_recommendations import recommend_flights  # noqa: E402
from services.transport_recommendations import recommend_transport  # noqa: E402

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Voyager AI API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_workflows: Dict[str, MultiAgentWorkflow] = {}


def get_workflow(model_id: str) -> MultiAgentWorkflow:
    """Lazily construct (and cache) a LangGraph workflow for the given resolved model id.

    One LangGraph workflow per model: switching models shouldn't require a
    server restart, and a workflow is cheap to build (it just wires up four
    agent objects) — only the chat model calls inside it talk to a network.
    """
    if model_id not in _workflows:
        _workflows[model_id] = create_workflow(model=model_id)
    return _workflows[model_id]


_orchestrators: Dict[tuple, object] = {}


def get_orchestrator(framework_id: str, model_id: str):
    """Lazily construct (and cache) an orchestrator for (framework_id, model_id).

    langgraph is the original default, so it reuses the existing `_workflows`
    cache via get_workflow() rather than a second parallel cache — this also
    means tests that monkeypatch module-level `get_workflow` keep working
    unchanged for the default framework (Phase 6 only adds a path alongside
    it, not instead of it).
    """
    if framework_id == "langgraph":
        return get_workflow(model_id)
    key = (framework_id, model_id)
    if key not in _orchestrators:
        _orchestrators[key] = build_orchestrator(framework_id, model=model_id)
    return _orchestrators[key]


def _run_guardrail_scan(text: str, source: str, db: Session) -> dict:
    """Scan `text`, log the result as a GuardrailEvent, and return the scan
    result dict (with `blocked` added) for the caller to act on."""
    result = scan_text(text)
    blocked = is_blocked(result)
    db.add(
        GuardrailEvent(
            source=source,
            text_excerpt=text[:500],
            risk=result["risk"],
            categories=result["categories"],
            blocked=blocked,
        )
    )
    db.commit()
    return {**result, "blocked": blocked}


@app.get("/api/health")
def health():
    return {"status": "ok", "config_valid": bool(Config.OPENAI_API_KEY)}


@app.get("/api/models", response_model=List[ModelInfoResponse])
def list_models():
    return [
        ModelInfoResponse(
            id=m.id,
            label=m.label,
            provider=m.provider,
            context_window=m.context_window,
            local=m.local,
            configured=is_configured(m.id),
        )
        for m in MODEL_REGISTRY.values()
    ]


@app.get("/api/frameworks", response_model=List[FrameworkInfoResponse])
def list_frameworks():
    return [
        FrameworkInfoResponse(id=f.id, label=f.label, description=f.description, available=f.available)
        for f in FRAMEWORK_REGISTRY.values()
    ]


@app.get("/api/agents", response_model=List[AgentInfoResponse])
def list_agents():
    return [AgentInfoResponse(**agent) for agent in AGENT_CATALOG]


# --- RAG Knowledge Base (Phase 7) -----------------------------------------------
# Free-text notes/guides about a destination, embedded and retrieved by
# similarity (app/rag). The research agent (app/agents/research_agent.py)
# automatically grounds itself in whatever's here for a matching destination.

@app.post("/api/knowledge", response_model=KnowledgeDocumentSummary, status_code=201)
def create_knowledge_document(payload: KnowledgeDocumentCreateRequest, db: Session = Depends(get_db)):
    scan = _run_guardrail_scan(f"{payload.title}\n{payload.content}", "knowledge_ingest", db)
    if scan["blocked"]:
        raise HTTPException(
            status_code=422,
            detail=f"Note rejected by the guardrails scanner (risk: {scan['risk']}, categories: {scan['categories']})",
        )

    try:
        document, chunk_count = ingest_document(payload.destination, payload.title, payload.content, db=db)
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return KnowledgeDocumentSummary(
        id=document.id,
        destination=document.destination,
        title=document.title,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


@app.get("/api/knowledge", response_model=List[KnowledgeDocumentSummary])
def list_knowledge_documents(db: Session = Depends(get_db)):
    return [KnowledgeDocumentSummary(**doc) for doc in list_documents(db=db)]


@app.get("/api/knowledge/search", response_model=List[KnowledgeSearchResult])
def search_knowledge_documents(
    query: str, destination: Optional[str] = None, top_k: int = 5, db: Session = Depends(get_db)
):
    try:
        results = search_knowledge(query, destination=destination, top_k=top_k, db=db)
    except EmbeddingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return [KnowledgeSearchResult(**r) for r in results]


@app.get("/api/trips", response_model=List[TripSummary])
def list_trips(db: Session = Depends(get_db)):
    return db.query(Trip).order_by(Trip.created_at.desc()).all()


def _committed_amount(trip_id: str, db: Session) -> float:
    """Real money only: confirmed bookings with a cost, plus logged expenses -
    the same definition TripBudget.tsx's frontend committed-total card uses.
    Never includes pending/cancelled bookings or LLM-estimated price ranges."""
    bookings = (
        db.query(BookingModel)
        .filter(BookingModel.trip_id == trip_id, BookingModel.status == "confirmed", BookingModel.cost.isnot(None))
        .all()
    )
    expenses = db.query(ExpenseModel).filter(ExpenseModel.trip_id == trip_id).all()
    return sum(b.cost for b in bookings) + sum(e.amount for e in expenses)


def _attach_derived_recommendations(trip: Trip, db: Session) -> None:
    """Computes budget_allocation/flight_recommendations fresh on every read
    (Phase 11) and sets them as plain instance attributes - not DB columns,
    just enough for Pydantic's from_attributes to pick them up on the
    TripDetail response. None when there's nothing to compute from, never a
    fabricated placeholder."""
    trip.budget_allocation = None
    if trip.budget_amount:
        committed = _committed_amount(trip.id, db)
        trip.budget_allocation = allocate_budget(
            total_budget=trip.budget_amount,
            budget_level=trip.budget,
            days=trip.days,
            traveler_count=trip.traveler_count or 1,
            committed_amount=committed,
            max_flight_budget=trip.max_flight_budget_amount,
            max_transport_budget=trip.max_transport_budget_amount,
        )

    trip.flight_recommendations = None
    flights = (trip.plan or {}).get("flights") if trip.plan else None
    if flights:
        trip.flight_recommendations = recommend_flights(
            flights,
            traveler_count=trip.traveler_count or 1,
            max_flight_budget=trip.max_flight_budget_amount,
        )

    trip.transport_recommendations = None
    if trip.plan:
        transportation = trip.plan.get("transportation")
        itinerary_days = (trip.plan.get("itinerary") or {}).get("itinerary")
        trip.transport_recommendations = recommend_transport(transportation, itinerary_days)


@app.get("/api/trips/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    _attach_derived_recommendations(trip, db)
    return trip


@app.post("/api/trips", response_model=TripDetail, status_code=201)
def create_trip(payload: TripCreateRequest, db: Session = Depends(get_db)):
    if payload.trip_type.lower() not in TRIP_TYPES:
        raise HTTPException(status_code=422, detail=f"trip_type must be one of {TRIP_TYPES}")
    if payload.budget.lower() not in BUDGET_LEVELS:
        raise HTTPException(status_code=422, detail=f"budget must be one of {BUDGET_LEVELS}")
    if payload.start_date:
        try:
            date.fromisoformat(payload.start_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="start_date must be in YYYY-MM-DD format")
    if payload.model and payload.model not in MODEL_REGISTRY:
        raise HTTPException(status_code=422, detail=f"model must be one of {list(MODEL_REGISTRY)}")
    if payload.framework and payload.framework not in FRAMEWORK_REGISTRY:
        raise HTTPException(status_code=422, detail=f"framework must be one of {list(FRAMEWORK_REGISTRY)}")

    scan = _run_guardrail_scan(payload.destination, "trip_destination", db)
    if scan["blocked"]:
        raise HTTPException(
            status_code=422,
            detail=f"Destination rejected by the guardrails scanner (risk: {scan['risk']}, categories: {scan['categories']})",
        )

    model_id = resolve_model(payload.model)
    if not is_configured(model_id):
        info = MODEL_REGISTRY[model_id]
        raise HTTPException(
            status_code=503,
            detail=f"Model '{model_id}' needs {info.requires_env} to be set on the server; it isn't configured",
        )

    framework_id = resolve_framework(payload.framework)
    if not is_framework_available(framework_id):
        raise HTTPException(
            status_code=503,
            detail=f"Framework '{framework_id}' isn't installed on the server",
        )

    trip = Trip(
        destination=payload.destination,
        days=payload.days,
        trip_type=payload.trip_type,
        budget=payload.budget,
        dietary_preferences=payload.dietary_preferences,
        model=model_id,
        framework=framework_id,
        status="planning",
        start_date=payload.start_date,
        origin=payload.origin,
        traveler_count=payload.traveler_count,
        max_flight_budget_amount=payload.max_flight_budget_amount,
        max_transport_budget_amount=payload.max_transport_budget_amount,
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    try:
        workflow = get_orchestrator(framework_id, model_id)
        result = workflow.plan_trip(
            destination=trip.destination,
            days=trip.days,
            trip_type=trip.trip_type,
            budget=trip.budget,
            dietary_preferences=trip.dietary_preferences,
            start_date=trip.start_date,
            origin=trip.origin,
        )
    except Exception as exc:  # workflow-level failure (e.g. provider outage)
        trip.status = "failed"
        trip.errors = [str(exc)]
        db.commit()
        db.refresh(trip)
        _attach_derived_recommendations(trip, db)
        return trip

    if result.get("success"):
        trip.status = "complete"
        trip.plan = result.get("plan")
        trip.errors = result.get("errors") or []
        trip.trace = result.get("trace") or []
    else:
        trip.status = "failed"
        trip.errors = [result.get("error", "Unknown planning error")]

    db.commit()
    db.refresh(trip)
    _attach_derived_recommendations(trip, db)
    return trip


def _get_trip_or_404(trip_id: str, db: Session) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.patch("/api/trips/{trip_id}", response_model=TripDetail)
def update_trip_budget(trip_id: str, payload: TripBudgetUpdate, db: Session = Depends(get_db)):
    trip = _get_trip_or_404(trip_id, db)
    trip.budget_amount = payload.budget_amount
    db.commit()
    db.refresh(trip)
    _attach_derived_recommendations(trip, db)
    return trip


@app.patch("/api/trips/{trip_id}/budget-caps", response_model=TripDetail)
def update_budget_caps(trip_id: str, payload: TravelBudgetCapsUpdate, db: Session = Depends(get_db)):
    """Sets traveler_count and/or per-category flight/transport budget
    ceilings independently of the overall budget_amount target. Recomputes
    budget_allocation and flight_recommendations fresh (same derived fields
    get_trip returns) - no itinerary/plan regeneration, since none of these
    fields feed into plan generation."""
    trip = _get_trip_or_404(trip_id, db)
    if payload.traveler_count is not None:
        trip.traveler_count = payload.traveler_count
    if payload.max_flight_budget_amount is not None:
        trip.max_flight_budget_amount = payload.max_flight_budget_amount
    if payload.max_transport_budget_amount is not None:
        trip.max_transport_budget_amount = payload.max_transport_budget_amount
    db.commit()
    db.refresh(trip)
    _attach_derived_recommendations(trip, db)
    return trip


# --- Per-section selection (Phase 10) ---------------------------------------------
# Lets a user pick one option from the plan's already-generated flights/accommodations
# list without regenerating the whole trip. Selecting a flight touches nothing else -
# flights don't feed into anything downstream today. Selecting an accommodation DOES
# re-run (only) the itinerary step, since the schedule's travel-time optimization
# depends on accommodation location - "recalculate only the affected section," not
# "change nothing," which is what the request actually asks for. Research/dining/
# flights are never re-run by either endpoint.

def _recompute_trace_entry(step: str, start: float, status: str, error: Optional[str] = None) -> Dict:
    entry = {"step": step, "duration_ms": round((time.monotonic() - start) * 1000, 1), "status": status}
    if error:
        entry["error"] = error
    return entry


@app.patch("/api/trips/{trip_id}/select-flight", response_model=TripDetail)
def select_flight(trip_id: str, payload: SelectIndexRequest, db: Session = Depends(get_db)):
    trip = _get_trip_or_404(trip_id, db)
    flights = (trip.plan or {}).get("flights") or []
    if payload.index >= len(flights):
        raise HTTPException(status_code=422, detail=f"index must be between 0 and {len(flights) - 1}")

    trip.selected_flight_index = payload.index
    db.commit()
    db.refresh(trip)
    _attach_derived_recommendations(trip, db)
    return trip


@app.patch("/api/trips/{trip_id}/select-accommodation", response_model=TripDetail)
def select_accommodation(trip_id: str, payload: SelectIndexRequest, db: Session = Depends(get_db)):
    trip = _get_trip_or_404(trip_id, db)
    accommodations = (trip.plan or {}).get("accommodations") or []
    if payload.index >= len(accommodations):
        raise HTTPException(status_code=422, detail=f"index must be between 0 and {len(accommodations) - 1}")

    selected = accommodations[payload.index]
    coords = selected.get("coordinates")
    accommodation_location = (coords["lat"], coords["lng"]) if coords else None

    start = time.monotonic()
    try:
        itinerary_agent = ItineraryAgent(model=trip.model)
        itinerary = itinerary_agent.create_schedule(
            attractions=(trip.plan or {}).get("attractions", []),
            days=trip.days,
            trip_type=trip.trip_type,
            destination=trip.destination,
            restaurants=(trip.plan or {}).get("restaurants", []),
            accommodation_location=accommodation_location,
        )
        trip.plan = {**trip.plan, "itinerary": itinerary}
        trip.trace = (trip.trace or []) + [_recompute_trace_entry("itinerary_recompute", start, "success")]
    except Exception as e:
        # The selection itself still succeeds even if the itinerary recompute
        # fails - the old itinerary just stays in place rather than being lost.
        trip.trace = (trip.trace or []) + [_recompute_trace_entry("itinerary_recompute", start, "error", str(e))]

    trip.selected_accommodation_index = payload.index
    db.commit()
    db.refresh(trip)
    _attach_derived_recommendations(trip, db)
    return trip


# --- Bookings & Wallet (Phase 4) -------------------------------------------------
# User-entered booking records (flight/hotel references, confirmations) — not a
# live booking integration. Real provider bookings are Phase 3's "booking handoff"
# and later a Level 3 authorized direct booking; this is the wallet that holds them.

@app.get("/api/trips/{trip_id}/bookings", response_model=List[Booking])
def list_bookings(trip_id: str, db: Session = Depends(get_db)):
    _get_trip_or_404(trip_id, db)
    return db.query(BookingModel).filter(BookingModel.trip_id == trip_id).order_by(BookingModel.created_at.desc()).all()


@app.post("/api/trips/{trip_id}/bookings", response_model=Booking, status_code=201)
def create_booking(trip_id: str, payload: BookingCreateRequest, db: Session = Depends(get_db)):
    _get_trip_or_404(trip_id, db)
    if payload.type not in BOOKING_TYPES:
        raise HTTPException(status_code=422, detail=f"type must be one of {BOOKING_TYPES}")

    booking = BookingModel(trip_id=trip_id, **payload.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@app.patch("/api/trips/{trip_id}/bookings/{booking_id}", response_model=Booking)
def update_booking_status(trip_id: str, booking_id: str, payload: BookingStatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in BOOKING_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {BOOKING_STATUSES}")
    booking = db.get(BookingModel, booking_id)
    if booking is None or booking.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = payload.status
    db.commit()
    db.refresh(booking)
    return booking


@app.delete("/api/trips/{trip_id}/bookings/{booking_id}", status_code=204)
def delete_booking(trip_id: str, booking_id: str, db: Session = Depends(get_db)):
    booking = db.get(BookingModel, booking_id)
    if booking is None or booking.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()


# --- Budget & Expenses (Phase 4) ------------------------------------------------

@app.get("/api/trips/{trip_id}/expenses", response_model=List[Expense])
def list_expenses(trip_id: str, db: Session = Depends(get_db)):
    _get_trip_or_404(trip_id, db)
    return db.query(ExpenseModel).filter(ExpenseModel.trip_id == trip_id).order_by(ExpenseModel.created_at.desc()).all()


@app.post("/api/trips/{trip_id}/expenses", response_model=Expense, status_code=201)
def create_expense(trip_id: str, payload: ExpenseCreateRequest, db: Session = Depends(get_db)):
    _get_trip_or_404(trip_id, db)
    if payload.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {EXPENSE_CATEGORIES}")

    expense = ExpenseModel(trip_id=trip_id, **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@app.delete("/api/trips/{trip_id}/expenses/{expense_id}", status_code=204)
def delete_expense(trip_id: str, expense_id: str, db: Session = Depends(get_db)):
    expense = db.get(ExpenseModel, expense_id)
    if expense is None or expense.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()


# --- Evaluations (Phase 8) -------------------------------------------------------
# A fixed set of canned trip-planning cases (app/evaluation), run against a real
# model/framework and graded automatically, so regressions (a broken agent, a
# misconfigured provider) show up as failing cases instead of a vibe check.

@app.post("/api/evaluations", response_model=EvaluationRunDetail, status_code=201)
def create_evaluation_run(payload: EvaluationRunRequest, db: Session = Depends(get_db)):
    if payload.model and payload.model not in MODEL_REGISTRY:
        raise HTTPException(status_code=422, detail=f"model must be one of {list(MODEL_REGISTRY)}")
    if payload.framework and payload.framework not in FRAMEWORK_REGISTRY:
        raise HTTPException(status_code=422, detail=f"framework must be one of {list(FRAMEWORK_REGISTRY)}")

    model_id = resolve_model(payload.model)
    framework_id = resolve_framework(payload.framework)
    if not is_framework_available(framework_id):
        raise HTTPException(status_code=503, detail=f"Framework '{framework_id}' isn't installed on the server")

    results = run_eval_suite(model=model_id, framework=framework_id)
    run = EvaluationRun(
        model=model_id,
        framework=framework_id,
        pass_count=sum(1 for r in results if r["passed"]),
        fail_count=sum(1 for r in results if not r["passed"]),
        results=results,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/evaluations", response_model=List[EvaluationRunSummary])
def list_evaluation_runs(db: Session = Depends(get_db)):
    return db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).all()


@app.get("/api/evaluations/{run_id}", response_model=EvaluationRunDetail)
def get_evaluation_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(EvaluationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run


@app.get("/api/evaluations/cases/list")
def list_evaluation_cases():
    return [{"id": c["id"], "description": c["description"]} for c in EVAL_CASES]


# --- Security Lab / Guardrails (Phase 9) ----------------------------------------
# Heuristic prompt-injection scanning (app/guardrails) applied to the two real
# injection surfaces in this app — RAG knowledge content and a trip's
# destination, both of which get concatenated straight into an agent's LLM
# prompt — plus an ad-hoc playground endpoint and an audit log of every scan.

@app.post("/api/guardrails/scan", response_model=GuardrailScanResult)
def run_guardrail_scan(payload: GuardrailScanRequest, db: Session = Depends(get_db)):
    return _run_guardrail_scan(payload.text, "manual_scan", db)


@app.get("/api/guardrails/events", response_model=List[GuardrailEventSummary])
def list_guardrail_events(db: Session = Depends(get_db)):
    return db.query(GuardrailEvent).order_by(GuardrailEvent.created_at.desc()).limit(100).all()


# --- Trip Documents (Phase 4, remaining scope) ----------------------------------
# File attachments per trip (ticket PDFs, passport scans, hotel vouchers),
# stored on local disk (app/documents.py) with metadata in the DB.

@app.post("/api/trips/{trip_id}/documents", response_model=TripDocumentSummary, status_code=201)
async def upload_trip_document(trip_id: str, db: Session = Depends(get_db), file: UploadFile = File(...)):
    _get_trip_or_404(trip_id, db)
    data = await file.read()
    try:
        meta = save_document_bytes(trip_id, file.filename or "upload", data)
    except DocumentTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    document = TripDocument(trip_id=trip_id, **meta)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@app.get("/api/trips/{trip_id}/documents", response_model=List[TripDocumentSummary])
def list_trip_documents(trip_id: str, db: Session = Depends(get_db)):
    _get_trip_or_404(trip_id, db)
    return (
        db.query(TripDocument)
        .filter(TripDocument.trip_id == trip_id)
        .order_by(TripDocument.created_at.desc())
        .all()
    )


def _get_document_or_404(trip_id: str, document_id: str, db: Session) -> TripDocument:
    document = db.get(TripDocument, document_id)
    if document is None or document.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.get("/api/trips/{trip_id}/documents/{document_id}/download")
def download_trip_document(trip_id: str, document_id: str, db: Session = Depends(get_db)):
    document = _get_document_or_404(trip_id, document_id, db)
    if not os.path.exists(document.stored_path):
        raise HTTPException(status_code=404, detail="File missing on server")
    return FileResponse(
        document.stored_path, filename=document.filename, media_type=document.content_type or "application/octet-stream"
    )


@app.delete("/api/trips/{trip_id}/documents/{document_id}", status_code=204)
def delete_trip_document(trip_id: str, document_id: str, db: Session = Depends(get_db)):
    document = _get_document_or_404(trip_id, document_id, db)
    delete_document_file(document.stored_path)
    db.delete(document)
    db.commit()


# --- Shareable trip links (Phase 4, remaining scope: "group collaboration") -----
# No multi-user accounts exist in this app (see the blueprint's audit), so
# "collaboration" here is scoped to what's buildable without inventing one: a
# secret per-trip link that lets a travel companion view the read-only plan,
# nothing more (no bookings, no budget, no documents — those stay private to
# whoever has the app open).

@app.post("/api/trips/{trip_id}/share", response_model=ShareLinkResponse)
def create_share_link(trip_id: str, db: Session = Depends(get_db)):
    trip = _get_trip_or_404(trip_id, db)
    if not trip.share_token:
        trip.share_token = secrets.token_urlsafe(16)
        db.commit()
        db.refresh(trip)
    return ShareLinkResponse(share_token=trip.share_token)


@app.delete("/api/trips/{trip_id}/share", status_code=204)
def revoke_share_link(trip_id: str, db: Session = Depends(get_db)):
    trip = _get_trip_or_404(trip_id, db)
    trip.share_token = None
    db.commit()


@app.get("/api/public/trips/{share_token}", response_model=PublicTripView)
def get_shared_trip(share_token: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.share_token == share_token).first()
    if trip is None:
        raise HTTPException(status_code=404, detail="Shared trip not found")
    return trip


# --- Real travel providers (Phase 3) --------------------------------------------
# Standalone, real-data lookup tools (RapidAPI's Flights Scraper Sky + Booking
# COM, and OpenWeatherMap) — deliberately kept separate from the LLM-based
# planning pipeline (app/workflow.py, app/orchestration) rather than fused
# into it; see the blueprint's Phase 3 delivery notes for why.

@app.get("/api/flights/autocomplete")
def flights_autocomplete(query: str):
    if not flights_api.is_configured():
        raise HTTPException(status_code=503, detail="RAPIDAPI_KEY not configured on the server")
    try:
        return flights_api.autocomplete_place(query)
    except FlightsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/flights/search", response_model=List[FlightOffer])
def flights_search(origin: str, destination: str, depart_date: str, currency: str = "USD"):
    if not flights_api.is_configured():
        raise HTTPException(status_code=503, detail="RAPIDAPI_KEY not configured on the server")
    try:
        offers = flights_api.search_one_way(origin, destination, depart_date, currency=currency)
    except FlightsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return [FlightOffer(**o) for o in offers]


@app.get("/api/hotels/autocomplete")
def hotels_autocomplete(query: str):
    if not hotels_api.is_configured():
        raise HTTPException(status_code=503, detail="RAPIDAPI_KEY not configured on the server")
    try:
        return hotels_api.search_destination(query)
    except HotelsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/hotels/search", response_model=List[HotelOffer])
def hotels_search(
    dest_id: str,
    search_type: str,
    checkin_date: str,
    checkout_date: str,
    adults: int = 2,
    room_qty: int = 1,
    currency: str = "USD",
):
    if not hotels_api.is_configured():
        raise HTTPException(status_code=503, detail="RAPIDAPI_KEY not configured on the server")
    try:
        offers = hotels_api.search_hotels(
            dest_id, search_type, checkin_date, checkout_date, adults=adults, room_qty=room_qty, currency=currency
        )
    except HotelsAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return [HotelOffer(**o) for o in offers]


@app.get("/api/weather/forecast", response_model=WeatherForecastResponse)
def weather_forecast(destination: str):
    if not weather_api.is_configured():
        raise HTTPException(status_code=503, detail="OPENWEATHER_API_KEY not configured on the server")
    try:
        return weather_api.get_forecast(destination)
    except WeatherAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/currency/convert", response_model=CurrencyConversion)
def currency_convert(amount: float, from_currency: str, to_currency: str):
    """Real, live exchange rate via Frankfurter (ECB reference rates, no API
    key needed) - see app/services/currency_api.py. 502 (not a fabricated
    rate) when the provider can't resolve the pair."""
    result = currency_api.convert(amount, from_currency, to_currency)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail=f"Could not resolve exchange rate for {from_currency.upper()} -> {to_currency.upper()}",
        )
    return result


@app.get("/api/currency/rates", response_model=CurrencyRates)
def currency_rates(base: str = "USD"):
    result = currency_api.list_rates(base)
    if result is None:
        raise HTTPException(status_code=502, detail=f"Could not fetch live rates for base currency {base.upper()}")
    return result


@app.get("/api/maps/search", response_model=List[PlaceResult])
def maps_search(query: str):
    if not ors_api.ORS_API_KEY:
        raise HTTPException(status_code=503, detail="ORS_API_KEY not configured on the server")
    try:
        return ors_api.search_places(query)
    except ORSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/maps/route", response_model=RouteResponse)
def maps_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    profile: str = "driving-car",
):
    if not ors_api.ORS_API_KEY:
        raise HTTPException(status_code=503, detail="ORS_API_KEY not configured on the server")
    try:
        return ors_api.get_route((origin_lat, origin_lng), (dest_lat, dest_lng), profile=profile)
    except ORSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
