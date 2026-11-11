"""
SQLAlchemy ORM models for persisted trips.

Named models_db.py (not models.py) to avoid colliding with the Pydantic
request/response schemas in schemas.py, and because "models" in this codebase
could otherwise be mistaken for LLM model config, which belongs to a later phase.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, JSON

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

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
