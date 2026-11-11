"""Pydantic request/response schemas for the FastAPI trip-planning API."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

TRIP_TYPES = ["historic", "adventure", "relaxation", "foodie", "cultural", "romantic", "nature"]
BUDGET_LEVELS = ["budget", "mid-range", "premium"]


class TripCreateRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=255, examples=["Goa, India"])
    days: int = Field(..., ge=1, le=30)
    trip_type: str = Field(..., examples=["foodie"])
    budget: str = Field("mid-range", examples=["mid-range"])
    dietary_preferences: List[str] = Field(default_factory=list)


class TripSummary(BaseModel):
    id: str
    destination: str
    days: int
    trip_type: str
    budget: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TripDetail(TripSummary):
    dietary_preferences: List[str]
    plan: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
