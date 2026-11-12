"""
Tests for the LangGraph workflow's observability trace (Phase 8).

Mocks the four agent classes the same way test_crewai_adapter.py does, so
these verify our own trace-accumulation wiring in app/workflow.py rather than
LangGraph's execution engine or a real agent/provider call.
"""
from unittest.mock import patch

from workflow import MultiAgentWorkflow


def _build_workflow_with_mocked_agents():
    with patch("workflow.ResearchAgent") as MockResearch, patch(
        "workflow.AccommodationAgent"
    ) as MockAccommodation, patch("workflow.DiningAgent") as MockDining, patch(
        "workflow.ItineraryAgent"
    ) as MockItinerary, patch("workflow.TransportAgent") as MockTransport:
        research_instance = MockResearch.return_value
        research_instance.find_attractions.return_value = [{"name": "Gateway of India"}]

        accommodation_instance = MockAccommodation.return_value
        accommodation_instance.find_accommodations.return_value = [
            {"name": "Taj Hotel", "coordinates": {"lat": 1.0, "lng": 2.0}}
        ]
        accommodation_instance.get_best_accommodation.return_value = {
            "name": "Taj Hotel",
            "coordinates": {"lat": 1.0, "lng": 2.0},
        }

        dining_instance = MockDining.return_value
        dining_instance.find_restaurants.return_value = [{"name": "Leopold Cafe"}]

        itinerary_instance = MockItinerary.return_value
        itinerary_instance.create_schedule.return_value = {"itinerary": [{"day": 1}]}

        transport_instance = MockTransport.return_value
        transport_instance.find_airport_transfer.return_value = None

        workflow = MultiAgentWorkflow(model="gpt-4o-mini")
        return workflow, {
            "research": research_instance,
            "accommodation": accommodation_instance,
            "dining": dining_instance,
            "itinerary": itinerary_instance,
            "transport": transport_instance,
        }


def test_plan_trip_trace_covers_all_four_steps_in_order():
    workflow, _ = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        result = workflow.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    assert result["success"] is True
    assert [t["step"] for t in result["trace"]] == [
        "research",
        "flights",
        "accommodation",
        "transportation",
        "dining",
        "itinerary",
    ]
    assert all(isinstance(t["duration_ms"], float) for t in result["trace"])
    flights_entry = next(t for t in result["trace"] if t["step"] == "flights")
    assert flights_entry["status"] == "skipped"  # no origin given in this test


def test_plan_trip_passes_start_date_through_to_accommodation_agent():
    workflow, mocks = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        workflow.plan_trip(
            destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10"
        )

    _, kwargs = mocks["accommodation"].find_accommodations.call_args
    assert kwargs["start_date"] == "2026-12-10"


def test_plan_trip_defaults_start_date_to_none():
    workflow, mocks = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation")

    _, kwargs = mocks["accommodation"].find_accommodations.call_args
    assert kwargs["start_date"] is None


def test_plan_trip_trace_records_error_status_for_failing_step():
    workflow, mocks = _build_workflow_with_mocked_agents()
    mocks["dining"].find_restaurants.side_effect = RuntimeError("provider down")

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        result = workflow.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    dining_entry = next(t for t in result["trace"] if t["step"] == "dining")
    assert dining_entry["status"] == "error"
    assert "provider down" in dining_entry["error"]
    # Downstream steps still ran (each node independently catches its own error).
    assert [t["step"] for t in result["trace"]] == [
        "research",
        "flights",
        "accommodation",
        "transportation",
        "dining",
        "itinerary",
    ]


def test_plan_trip_skips_flight_search_without_origin():
    workflow, _ = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        result = workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10")

    assert result["plan"]["flights"] == []
    flights_entry = next(t for t in result["trace"] if t["step"] == "flights")
    assert flights_entry["status"] == "skipped"


def test_plan_trip_searches_real_flights_when_origin_and_date_given():
    workflow, _ = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ), patch("workflow.flights_api.search_flights_for_trip", return_value=[{"price": "₹4,977", "source": "real"}]) as mock_search:
        result = workflow.plan_trip(
            destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10", origin="Mumbai"
        )

    mock_search.assert_called_once_with("Mumbai", "Goa, India", "2026-12-10")
    assert result["plan"]["flights"] == [{"price": "₹4,977", "source": "real"}]
    flights_entry = next(t for t in result["trace"] if t["step"] == "flights")
    assert flights_entry["status"] == "success"


def test_plan_trip_flights_error_does_not_fabricate_data():
    workflow, _ = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ), patch("workflow.flights_api.search_flights_for_trip", side_effect=RuntimeError("provider down")):
        result = workflow.plan_trip(
            destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10", origin="Mumbai"
        )

    assert result["plan"]["flights"] == []
    flights_entry = next(t for t in result["trace"] if t["step"] == "flights")
    assert flights_entry["status"] == "error"


def test_plan_trip_skips_transportation_without_accommodation_location():
    with patch("workflow.ResearchAgent") as MockResearch, patch(
        "workflow.AccommodationAgent"
    ) as MockAccommodation, patch("workflow.DiningAgent") as MockDining, patch(
        "workflow.ItineraryAgent"
    ) as MockItinerary, patch("workflow.TransportAgent") as MockTransport:
        MockResearch.return_value.find_attractions.return_value = []
        MockAccommodation.return_value.find_accommodations.return_value = []
        MockDining.return_value.find_restaurants.return_value = []
        MockItinerary.return_value.create_schedule.return_value = {}
        workflow = MultiAgentWorkflow(model="gpt-4o-mini")

        with patch("workflow.get_context_for_destination", return_value=""), patch(
            "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
        ):
            result = workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation")

        MockTransport.return_value.find_airport_transfer.assert_not_called()

    assert result["plan"]["transportation"] is None
    transportation_entry = next(t for t in result["trace"] if t["step"] == "transportation")
    assert transportation_entry["status"] == "skipped"


def test_plan_trip_finds_real_airport_transfer_when_accommodation_located():
    workflow, mocks = _build_workflow_with_mocked_agents()
    mocks["transport"].find_airport_transfer.return_value = {
        "mode": "driving",
        "from": "Goa, India Airport",
        "to": "accommodation",
        "distance_km": 4.2,
        "duration_h": 0.15,
        "geometry": [],
        "source": "real",
    }

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        result = workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation")

    mocks["transport"].find_airport_transfer.assert_called_once_with("Goa, India", (1.0, 2.0))
    assert result["plan"]["transportation"]["distance_km"] == 4.2
    transportation_entry = next(t for t in result["trace"] if t["step"] == "transportation")
    assert transportation_entry["status"] == "success"


def test_plan_trip_transportation_error_does_not_fabricate_data():
    workflow, mocks = _build_workflow_with_mocked_agents()
    mocks["transport"].find_airport_transfer.side_effect = RuntimeError("ORS down")

    with patch("workflow.get_context_for_destination", return_value=""), patch(
        "workflow.geocode_attractions", side_effect=lambda attractions, destination: attractions
    ):
        result = workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation")

    assert result["plan"]["transportation"] is None
    transportation_entry = next(t for t in result["trace"] if t["step"] == "transportation")
    assert transportation_entry["status"] == "error"
