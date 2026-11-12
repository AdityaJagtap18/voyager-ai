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
    framework: Optional[str] = Field(None, description="Orchestration framework id from GET /api/frameworks; omit for the default (langgraph)")
    start_date: Optional[str] = Field(
        None,
        examples=["2026-12-10"],
        description="Optional check-in date (YYYY-MM-DD). When set and RAPIDAPI_KEY is configured, the "
        "accommodation agent grounds its recommendations in real, live hotel data instead of LLM-generated ones.",
    )
    origin: Optional[str] = Field(
        None,
        examples=["Mumbai"],
        description="Optional departure city/airport. When set together with start_date and RAPIDAPI_KEY is "
        "configured, the itinerary is grounded in a real flight search instead of having no flight data at all.",
    )


class TripSummary(BaseModel):
    id: str
    destination: str
    days: int
    trip_type: str
    budget: str
    status: str
    created_at: datetime
    start_date: Optional[str] = None
    origin: Optional[str] = None
    selected_accommodation_index: Optional[int] = None
    selected_flight_index: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class TripDetail(TripSummary):
    dietary_preferences: List[str]
    plan: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    budget_amount: Optional[float] = None
    model: Optional[str] = None
    framework: Optional[str] = None
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    share_token: Optional[str] = None


class SelectIndexRequest(BaseModel):
    """Picks one option from the trip's already-generated plan.accommodations/plan.flights
    list by index - there's no separate id for these options, just their position."""
    index: int = Field(..., ge=0)


class ModelInfoResponse(BaseModel):
    id: str
    label: str
    provider: str
    context_window: int
    local: bool
    configured: bool


class FrameworkInfoResponse(BaseModel):
    id: str
    label: str
    description: str
    available: bool


class AgentInfoResponse(BaseModel):
    id: str
    name: str
    role: str
    goal: str
    data_source: str


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


class KnowledgeDocumentCreateRequest(BaseModel):
    destination: str = Field(..., min_length=2, max_length=255, examples=["Goa, India"])
    title: str = Field(..., min_length=1, max_length=255, examples=["Local tips"])
    content: str = Field(..., min_length=20, max_length=20000)


class KnowledgeDocumentSummary(BaseModel):
    id: str
    destination: str
    title: str
    chunk_count: int
    created_at: datetime


class KnowledgeSearchResult(BaseModel):
    document_id: str
    document_title: str
    destination: str
    chunk_text: str
    score: float


class EvaluationRunRequest(BaseModel):
    model: Optional[str] = Field(None, description="Model id to evaluate; omit for the configured default")
    framework: Optional[str] = Field(None, description="Orchestration framework id to evaluate; omit for the default (langgraph)")


class EvaluationCaseResult(BaseModel):
    case_id: str
    description: str
    passed: bool
    reason: str
    duration_ms: float


class EvaluationRunSummary(BaseModel):
    id: str
    model: Optional[str]
    framework: Optional[str]
    pass_count: int
    fail_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunDetail(EvaluationRunSummary):
    results: List[EvaluationCaseResult]


class GuardrailScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000)


class GuardrailScanResult(BaseModel):
    risk: str
    categories: List[str]
    matches: List[str]
    blocked: bool


class TripDocumentSummary(BaseModel):
    id: str
    trip_id: str
    filename: str
    content_type: Optional[str]
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShareLinkResponse(BaseModel):
    share_token: str


class PublicTripView(BaseModel):
    destination: str
    days: int
    trip_type: str
    budget: str
    status: str
    plan: Optional[Dict[str, Any]] = None


class FlightOffer(BaseModel):
    price: Optional[str] = None
    price_raw: Optional[float] = None
    currency: str
    airline: Optional[str] = None
    duration_minutes: Optional[int] = None
    stops: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure: Optional[str] = None
    arrival: Optional[str] = None


class HotelOffer(BaseModel):
    hotel_id: Optional[int] = None
    name: Optional[str] = None
    price_formatted: Optional[str] = None
    price_raw: Optional[float] = None
    currency: str
    review_score: Optional[float] = None
    review_score_word: Optional[str] = None
    star_rating: Optional[int] = None
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WeatherDay(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    description: Optional[str] = None
    icon: Optional[str] = None


class WeatherLocation(BaseModel):
    name: str
    country: Optional[str] = None


class WeatherForecastResponse(BaseModel):
    location: WeatherLocation
    days: List[WeatherDay]


class PlaceResult(BaseModel):
    label: Optional[str] = None
    lat: float
    lng: float


class RouteResponse(BaseModel):
    distance_km: float
    duration_h: float
    geometry: List[List[float]]


class GuardrailEventSummary(BaseModel):
    id: str
    source: str
    text_excerpt: str
    risk: str
    categories: List[str]
    blocked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
