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
    ) as MockItinerary:
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

        workflow = MultiAgentWorkflow(model="gpt-4o-mini")
        return workflow, {
            "research": research_instance,
            "accommodation": accommodation_instance,
            "dining": dining_instance,
            "itinerary": itinerary_instance,
        }


def test_plan_trip_trace_covers_all_four_steps_in_order():
    workflow, _ = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""):
        result = workflow.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    assert result["success"] is True
    assert [t["step"] for t in result["trace"]] == ["research", "accommodation", "dining", "itinerary"]
    assert all(t["status"] == "success" for t in result["trace"])
    assert all(isinstance(t["duration_ms"], float) for t in result["trace"])


def test_plan_trip_passes_start_date_through_to_accommodation_agent():
    workflow, mocks = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""):
        workflow.plan_trip(
            destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10"
        )

    _, kwargs = mocks["accommodation"].find_accommodations.call_args
    assert kwargs["start_date"] == "2026-12-10"


def test_plan_trip_defaults_start_date_to_none():
    workflow, mocks = _build_workflow_with_mocked_agents()

    with patch("workflow.get_context_for_destination", return_value=""):
        workflow.plan_trip(destination="Goa, India", days=5, trip_type="relaxation")

    _, kwargs = mocks["accommodation"].find_accommodations.call_args
    assert kwargs["start_date"] is None


def test_plan_trip_trace_records_error_status_for_failing_step():
    workflow, mocks = _build_workflow_with_mocked_agents()
    mocks["dining"].find_restaurants.side_effect = RuntimeError("provider down")

    with patch("workflow.get_context_for_destination", return_value=""):
        result = workflow.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    dining_entry = next(t for t in result["trace"] if t["step"] == "dining")
    assert dining_entry["status"] == "error"
    assert "provider down" in dining_entry["error"]
    # Downstream steps still ran (each node independently catches its own error).
    assert [t["step"] for t in result["trace"]] == ["research", "accommodation", "dining", "itinerary"]
