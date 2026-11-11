import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point the API at an isolated temp SQLite file before anything imports app.db,
# so these tests never touch a developer's real data/voyager.db.
_TMP_DB = os.path.join(tempfile.gettempdir(), "voyager_test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app import api as api_module  # noqa: E402
from app.db import Base  # noqa: E402

engine = create_engine(f"sqlite:///{_TMP_DB}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


api_module.app.dependency_overrides[api_module.get_db] = _override_get_db
client = TestClient(api_module.app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_trip_requires_valid_trip_type(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", "sk-test")
    resp = client.post("/api/trips", json={
        "destination": "Goa, India",
        "days": 3,
        "trip_type": "not-a-real-type",
        "budget": "mid-range",
    })
    assert resp.status_code == 422


def test_create_trip_fails_without_openai_key(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", None)
    resp = client.post("/api/trips", json={
        "destination": "Goa, India",
        "days": 3,
        "trip_type": "foodie",
        "budget": "mid-range",
    })
    assert resp.status_code == 503


def test_create_and_fetch_trip(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", "sk-test")

    fake_workflow = MagicMock()
    fake_workflow.plan_trip.return_value = {
        "success": True,
        "plan": {
            "attractions": [{"name": "Baga Beach"}],
            "itinerary": {"day_1": []},
            "restaurants": [{"name": "Souza Lobo"}],
            "accommodations": [{"name": "Taj Fort Aguada"}],
        },
        "errors": [],
    }
    monkeypatch.setattr(api_module, "get_workflow", lambda: fake_workflow)

    create_resp = client.post("/api/trips", json={
        "destination": "Goa, India",
        "days": 3,
        "trip_type": "foodie",
        "budget": "mid-range",
        "dietary_preferences": ["vegetarian"],
    })
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["status"] == "complete"
    assert body["plan"]["attractions"][0]["name"] == "Baga Beach"
    trip_id = body["id"]

    get_resp = client.get(f"/api/trips/{trip_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["destination"] == "Goa, India"

    list_resp = client.get("/api/trips")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_create_trip_records_workflow_failure(monkeypatch):
    monkeypatch.setattr(api_module.Config, "OPENAI_API_KEY", "sk-test")

    fake_workflow = MagicMock()
    fake_workflow.plan_trip.return_value = {"success": False, "error": "provider down"}
    monkeypatch.setattr(api_module, "get_workflow", lambda: fake_workflow)

    resp = client.post("/api/trips", json={
        "destination": "Goa, India",
        "days": 3,
        "trip_type": "foodie",
        "budget": "mid-range",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"
    assert body["errors"] == ["provider down"]


def test_get_unknown_trip_returns_404():
    resp = client.get("/api/trips/does-not-exist")
    assert resp.status_code == 404


def _create_test_trip() -> str:
    """Insert a trip directly (bypassing the workflow) for bookings/expenses tests."""
    db = TestingSessionLocal()
    trip = api_module.Trip(destination="Goa, India", days=3, trip_type="foodie", budget="mid-range", status="complete")
    db.add(trip)
    db.commit()
    db.refresh(trip)
    trip_id = trip.id
    db.close()
    return trip_id


def test_set_trip_budget():
    trip_id = _create_test_trip()
    resp = client.patch(f"/api/trips/{trip_id}", json={"budget_amount": 50000})
    assert resp.status_code == 200
    assert resp.json()["budget_amount"] == 50000


def test_booking_crud_lifecycle():
    trip_id = _create_test_trip()

    create_resp = client.post(f"/api/trips/{trip_id}/bookings", json={
        "type": "flight",
        "title": "BOM -> GOI",
        "reference": "6E123",
        "cost": 4500,
    })
    assert create_resp.status_code == 201
    booking = create_resp.json()
    assert booking["status"] == "pending"
    booking_id = booking["id"]

    list_resp = client.get(f"/api/trips/{trip_id}/bookings")
    assert len(list_resp.json()) == 1

    confirm_resp = client.patch(f"/api/trips/{trip_id}/bookings/{booking_id}", json={"status": "confirmed"})
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    delete_resp = client.delete(f"/api/trips/{trip_id}/bookings/{booking_id}")
    assert delete_resp.status_code == 204
    assert client.get(f"/api/trips/{trip_id}/bookings").json() == []


def test_booking_rejects_invalid_type():
    trip_id = _create_test_trip()
    resp = client.post(f"/api/trips/{trip_id}/bookings", json={"type": "spaceship", "title": "Mars"})
    assert resp.status_code == 422


def test_expense_crud_lifecycle():
    trip_id = _create_test_trip()

    create_resp = client.post(f"/api/trips/{trip_id}/expenses", json={
        "category": "food",
        "description": "Beach shack dinner",
        "amount": 1200,
    })
    assert create_resp.status_code == 201
    expense_id = create_resp.json()["id"]

    list_resp = client.get(f"/api/trips/{trip_id}/expenses")
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["amount"] == 1200

    delete_resp = client.delete(f"/api/trips/{trip_id}/expenses/{expense_id}")
    assert delete_resp.status_code == 204
    assert client.get(f"/api/trips/{trip_id}/expenses").json() == []


def test_expense_rejects_invalid_category():
    trip_id = _create_test_trip()
    resp = client.post(f"/api/trips/{trip_id}/expenses", json={"category": "bribes", "amount": 100})
    assert resp.status_code == 422


def test_bookings_and_expenses_404_for_unknown_trip():
    assert client.get("/api/trips/nope/bookings").status_code == 404
    assert client.post("/api/trips/nope/bookings", json={"type": "flight", "title": "x"}).status_code == 404
    assert client.get("/api/trips/nope/expenses").status_code == 404
    assert client.post("/api/trips/nope/expenses", json={"category": "food", "amount": 1}).status_code == 404
