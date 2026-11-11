"""
SQLAlchemy ORM models for persisted trips.

Named models_db.py (not models.py) to avoid colliding with the Pydantic
request/response schemas in schemas.py, and because "models" in this codebase
could otherwise be mistaken for LLM model config, which belongs to a later phase.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON

from app.db import Base


def _new_id() -> str:
    return uuid.uuid4().hex


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String(32), primary_key=True, default=_new_id)
    destination = Column(String(255), nullable=False)
    days = Column(Integer, nullable=False)
    trip_type = Column(String(50), nullable=False)
    budget = Column(String(50), nullable=False, default="mid-range")
    dietary_preferences = Column(JSON, nullable=False, default=list)

    status = Column(String(20), nullable=False, default="planning")  # planning | complete | failed
    plan = Column(JSON, nullable=True)  # {attractions, itinerary, restaurants, accommodations}
    errors = Column(JSON, nullable=False, default=list)

    # Phase 4: user-set budget target this trip's expenses are tracked against.
    # Separate from the `budget` level above (budget/mid-range/premium), which
    # only steers what the agents recommend.
    budget_amount = Column(Float, nullable=True)

    # Phase 5: which model gateway id (app/llm_gateway.py's MODEL_REGISTRY) was
    # actually used to plan this trip — recorded for comparison/audit, not just
    # requested-and-forgotten.
    model = Column(String(100), nullable=True)

    # Phase 6: which orchestration framework (app/orchestration's
    # FRAMEWORK_REGISTRY — "langgraph" or "crewai") actually ran this trip.
    framework = Column(String(50), nullable=True)

    # Phase 8: per-agent-step timing/status trace emitted by the orchestrator
    # that ran this trip ({step, duration_ms, status, error?} per entry) —
    # observability into where time was spent and what failed, if anything.
    trace = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Booking types/status kept as free-text string columns (not a DB enum) so adding
# a new one later is a frontend-only change, consistent with how Trip.status works.
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(32), primary_key=True, default=_new_id)
    trip_id = Column(String(32), ForeignKey("trips.id"), nullable=False, index=True)

    type = Column(String(20), nullable=False)  # flight | hotel | activity | other
    title = Column(String(255), nullable=False)
    reference = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | confirmed | cancelled
    cost = Column(Float, nullable=True)
    notes = Column(String(2000), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Phase 7: RAG knowledge base. A document (e.g. a traveler's notes or a guide
# for a destination) is split into chunks, each embedded separately so search
# can retrieve the specific passage that matches a query instead of the whole
# document.
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(32), primary_key=True, default=_new_id)
    destination = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(32), primary_key=True, default=_new_id)
    document_id = Column(String(32), ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # list[float]


# Phase 8: a run of the evaluation harness (app/evaluation/__init__.py) against
# a fixed set of canned cases, for one model/framework combination.
class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(32), primary_key=True, default=_new_id)
    model = Column(String(100), nullable=True)
    framework = Column(String(50), nullable=True)

    pass_count = Column(Integer, nullable=False, default=0)
    fail_count = Column(Integer, nullable=False, default=0)
    results = Column(JSON, nullable=False, default=list)  # [{case_id, passed, reason, duration_ms}]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(32), primary_key=True, default=_new_id)
    trip_id = Column(String(32), ForeignKey("trips.id"), nullable=False, index=True)

    category = Column(String(50), nullable=False)  # flights | accommodation | food | transport | activities | shopping | misc
    description = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
