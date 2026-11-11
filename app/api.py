"""
Voyager AI — FastAPI backend (Phase 2).

Wraps the existing LangGraph multi-agent workflow (app/workflow.py) behind a
REST API and persists trips to a database (SQLite by default, Postgres via
DATABASE_URL — see app/db.py). The agents themselves are untouched.

Run with:
    uvicorn app.api:app --reload
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Mirror streamlit_app.py's sys.path setup: the agent modules (workflow.py and
# everything it imports) use bare imports like `from config import Config`,
# which only resolve if app/ itself is on sys.path, not just the repo root.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from app.config import Config  # noqa: E402
from app.db import get_db, init_db  # noqa: E402
from app.models_db import Trip  # noqa: E402
from app.schemas import BUDGET_LEVELS, TRIP_TYPES, TripCreateRequest, TripDetail, TripSummary  # noqa: E402
from app.workflow import create_workflow  # noqa: E402

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

_workflow = None


def get_workflow():
    """Lazily construct the LangGraph workflow (requires OPENAI_API_KEY)."""
    global _workflow
    if _workflow is None:
        _workflow = create_workflow()
    return _workflow


@app.get("/api/health")
def health():
    return {"status": "ok", "config_valid": bool(Config.OPENAI_API_KEY)}


@app.get("/api/trips", response_model=List[TripSummary])
def list_trips(db: Session = Depends(get_db)):
    return db.query(Trip).order_by(Trip.created_at.desc()).all()


@app.get("/api/trips/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: str, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@app.post("/api/trips", response_model=TripDetail, status_code=201)
def create_trip(payload: TripCreateRequest, db: Session = Depends(get_db)):
    if payload.trip_type.lower() not in TRIP_TYPES:
        raise HTTPException(status_code=422, detail=f"trip_type must be one of {TRIP_TYPES}")
    if payload.budget.lower() not in BUDGET_LEVELS:
        raise HTTPException(status_code=422, detail=f"budget must be one of {BUDGET_LEVELS}")
    if not Config.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Server is missing OPENAI_API_KEY; cannot plan trips")

    trip = Trip(
        destination=payload.destination,
        days=payload.days,
        trip_type=payload.trip_type,
        budget=payload.budget,
        dietary_preferences=payload.dietary_preferences,
        status="planning",
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    try:
        workflow = get_workflow()
        result = workflow.plan_trip(
            destination=trip.destination,
            days=trip.days,
            trip_type=trip.trip_type,
            budget=trip.budget,
            dietary_preferences=trip.dietary_preferences,
        )
    except Exception as exc:  # workflow-level failure (e.g. provider outage)
        trip.status = "failed"
        trip.errors = [str(exc)]
        db.commit()
        db.refresh(trip)
        return trip

    if result.get("success"):
        trip.status = "complete"
        trip.plan = result.get("plan")
        trip.errors = result.get("errors") or []
    else:
        trip.status = "failed"
        trip.errors = [result.get("error", "Unknown planning error")]

    db.commit()
    db.refresh(trip)
    return trip
