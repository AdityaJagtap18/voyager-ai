"""Pydantic request/response schemas for the FastAPI trip-planning API."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

TRIP_TYPES = ["historic", "adventure", "relaxation", "foodie", "cultural", "romantic", "nature"]
BUDGET_LEVELS = ["budget", "mid-range", "premium"]
BOOKING_TYPES = ["flight", "hotel", "activity", "other"]
BOOKING_STATUSES = ["pending", "confirmed", "cancelled"]
EXPENSE_CATEGORIES = ["flights", "accommodation", "food", "transport", "activities", "shopping", "misc"]


class TripCreateRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=255, examples=["Goa, India"])
    days: int = Field(..., ge=1, le=30)
    trip_type: str = Field(..., examples=["foodie"])
    budget: str = Field("mid-range", examples=["mid-range"])
    dietary_preferences: List[str] = Field(default_factory=list)
    model: Optional[str] = Field(None, description="Model id from GET /api/models; omit for the configured default")


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
    budget_amount: Optional[float] = None
    model: Optional[str] = None


class ModelInfoResponse(BaseModel):
    id: str
    label: str
    provider: str
    context_window: int
    local: bool
    configured: bool


class TripBudgetUpdate(BaseModel):
    budget_amount: float = Field(..., ge=0)


class BookingCreateRequest(BaseModel):
    type: str
    title: str = Field(..., min_length=1, max_length=255)
    reference: Optional[str] = Field(None, max_length=100)
    cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class BookingStatusUpdate(BaseModel):
    status: str


class Booking(BaseModel):
    id: str
    trip_id: str
    type: str
    title: str
    reference: Optional[str]
    status: str
    cost: Optional[float]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseCreateRequest(BaseModel):
    category: str
    description: Optional[str] = Field(None, max_length=255)
    amount: float = Field(..., gt=0)


class Expense(BaseModel):
    id: str
    trip_id: str
    category: str
    description: Optional[str]
    amount: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
