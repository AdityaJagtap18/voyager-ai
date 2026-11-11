"""
Tests for the CrewAI orchestration adapter (app/orchestration/crewai_adapter.py).

Mocks the four agent classes (same pattern as test_research_agent.py) and
replaces crewai's Crew with a fake whose kickoff() just runs each task's one
tool in order — simulating a CrewAI LLM that reliably decides "call my
tool", without needing a real model call. This verifies our wiring (agents,
tasks, context passing, final dict assembly) rather than CrewAI's own
execution engine, which isn't ours to test.
"""
import pytest

crewai = pytest.importorskip("crewai")

from unittest.mock import MagicMock, patch

from orchestration.crewai_adapter import CrewAIOrchestrator


class _FakeCrew:
    """Stands in for crewai.Crew: kickoff() runs each task's tool in order."""

    def __init__(self, agents, tasks, process=None, verbose=False):
        self.tasks = tasks

    def kickoff(self):
        for task in self.tasks:
            task.tools[0].run()


def _build_orchestrator_with_mocked_agents():
    with patch("orchestration.crewai_adapter.ResearchAgent") as MockResearch, patch(
        "orchestration.crewai_adapter.AccommodationAgent"
    ) as MockAccommodation, patch("orchestration.crewai_adapter.DiningAgent") as MockDining, patch(
        "orchestration.crewai_adapter.ItineraryAgent"
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

        orchestrator = CrewAIOrchestrator(model="gpt-4o-mini")
        return orchestrator, {
            "research": research_instance,
            "accommodation": accommodation_instance,
            "dining": dining_instance,
            "itinerary": itinerary_instance,
        }


def test_plan_trip_calls_all_four_agents_in_order_and_assembles_plan():
    orchestrator, mocks = _build_orchestrator_with_mocked_agents()

    with patch("orchestration.crewai_adapter.Crew", _FakeCrew), patch(
        "orchestration.crewai_adapter.get_context_for_destination", return_value=""
    ):
        result = orchestrator.plan_trip(
            destination="Mumbai, India", days=2, trip_type="historic", budget="mid-range", dietary_preferences=["vegetarian"]
        )

    mocks["research"].find_attractions.assert_called_once_with(
        destination="Mumbai, India", trip_type="historic", days=2, knowledge_context=""
    )
    mocks["accommodation"].find_accommodations.assert_called_once()
    mocks["dining"].find_restaurants.assert_called_once()
    mocks["itinerary"].create_schedule.assert_called_once()

    assert result["success"] is True
    assert result["plan"]["attractions"] == [{"name": "Gateway of India"}]
    assert result["plan"]["accommodations"][0]["name"] == "Taj Hotel"
    assert result["plan"]["restaurants"] == [{"name": "Leopold Cafe"}]
    assert result["plan"]["itinerary"] == {"itinerary": [{"day": 1}]}
    assert result["errors"] == []
    assert [t["step"] for t in result["trace"]] == ["research", "accommodation", "dining", "itinerary"]
    assert all(t["status"] == "success" for t in result["trace"])


def test_plan_trip_passes_start_date_through_to_accommodation_agent():
    orchestrator, mocks = _build_orchestrator_with_mocked_agents()

    with patch("orchestration.crewai_adapter.Crew", _FakeCrew), patch(
        "orchestration.crewai_adapter.get_context_for_destination", return_value=""
    ):
        orchestrator.plan_trip(
            destination="Goa, India", days=5, trip_type="relaxation", start_date="2026-12-10"
        )

    _, kwargs = mocks["accommodation"].find_accommodations.call_args
    assert kwargs["start_date"] == "2026-12-10"


def test_plan_trip_collects_errors_without_crashing():
    orchestrator, mocks = _build_orchestrator_with_mocked_agents()
    mocks["research"].find_attractions.side_effect = RuntimeError("provider down")

    with patch("orchestration.crewai_adapter.Crew", _FakeCrew), patch(
        "orchestration.crewai_adapter.get_context_for_destination", return_value=""
    ):
        result = orchestrator.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    assert result["success"] is True  # the crew itself didn't crash, just one tool errored
    assert result["plan"]["attractions"] == []
    assert "provider down" in result["errors"][0]
    assert result["trace"][0]["step"] == "research"
    assert result["trace"][0]["status"] == "error"
    assert "provider down" in result["trace"][0]["error"]


def test_plan_trip_reports_failure_if_crew_kickoff_raises():
    orchestrator, _ = _build_orchestrator_with_mocked_agents()

    broken_crew = MagicMock()
    broken_crew.kickoff.side_effect = RuntimeError("litellm.AuthenticationError")
    with patch("orchestration.crewai_adapter.Crew", return_value=broken_crew), patch(
        "orchestration.crewai_adapter.get_context_for_destination", return_value=""
    ):
        result = orchestrator.plan_trip(destination="Mumbai, India", days=2, trip_type="historic")

    assert result["success"] is False
    assert "AuthenticationError" in result["error"]
