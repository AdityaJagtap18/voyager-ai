"""
Regression tests for the itinerary scheduling bug: every activity on a day
used to be stamped with the same hardcoded "09:00" whenever dining
integration didn't run (no restaurants found, or no accommodation
coordinates - see app/agents/itinerary_agent.py create_schedule). These
tests cover the exact failure pattern plus the scheduling rules the fix
is supposed to guarantee.
"""
from unittest.mock import patch

from agents.itinerary_agent import ItineraryAgent


def _agent() -> ItineraryAgent:
    with patch("agents.itinerary_agent.get_chat_model"):
        return ItineraryAgent()


def _attraction(name: str, duration: str = "2 hours", coords=None) -> dict:
    attr = {"name": name, "duration": duration, "category": "sightseeing", "description": "", "best_time": "anytime"}
    if coords is not None:
        attr["coordinates"] = {"lat": coords[0], "lng": coords[1]}
    return attr


def _activity_times(schedule: dict, day: int = 1) -> list:
    day_plan = next(d for d in schedule["itinerary"] if d["day"] == day)
    return [a["time"] for a in day_plan["activities"] if a["type"] == "attraction"]


def test_exact_failure_pattern_no_restaurants_no_accommodation():
    """The reported bug: multiple same-day activities all show 09:00 when
    restaurants=[] and accommodation_location=None (the common real-world
    trigger - an LLM-sourced accommodation with no coordinates)."""
    agent = _agent()
    attractions = [_attraction(f"Attraction {i}") for i in range(4)]

    schedule = agent.create_schedule(
        attractions=attractions,
        days=1,
        trip_type="relaxation",
        destination="Nowhereland",
        restaurants=[],
        accommodation_location=None,
    )

    times = _activity_times(schedule)
    assert len(times) == 4
    # The bug: all four would be "09:00". The fix: strictly increasing.
    assert len(set(times)) == len(times), f"activities were not scheduled distinctly: {times}"
    assert times == sorted(times)
    assert times[0] == "09:00"
    assert times[1] != "09:00"


def test_no_restaurants_still_schedules_sequentially_without_accommodation():
    """Same as above but accommodation_location is falsy for a different
    reason (empty tuple-like value) - the scheduling must not depend on it."""
    agent = _agent()
    attractions = [_attraction("A"), _attraction("B"), _attraction("C")]

    schedule = agent.create_schedule(
        attractions=attractions, days=1, trip_type="historic", destination="X", restaurants=None,
        accommodation_location=None,
    )

    times = _activity_times(schedule)
    assert len(set(times)) == 3


def test_consecutive_activities_do_not_overlap_and_respect_duration():
    agent = _agent()
    attractions = [
        _attraction("Museum", duration="3 hours"),
        _attraction("Park", duration="1 hours"),
    ]

    schedule = agent.create_schedule(
        attractions=attractions, days=1, trip_type="cultural", destination="X", restaurants=[],
        accommodation_location=None,
    )

    day = schedule["itinerary"][0]
    attraction_activities = [a for a in day["activities"] if a["type"] == "attraction"]
    first, second = attraction_activities[0], attraction_activities[1]

    first_start_h, first_start_m = map(int, first["time"].split(":"))
    second_start_h, second_start_m = map(int, second["time"].split(":"))
    first_start = first_start_h + first_start_m / 60
    second_start = second_start_h + second_start_m / 60

    # Museum is 3h + a 15-min buffer, so Park must start no earlier than that.
    assert second_start >= first_start + 3.0
    assert first["duration_minutes"] == 180
    assert second["duration_minutes"] == 60


def test_travel_time_is_reflected_in_the_next_activity_start():
    agent = _agent()
    attractions = [
        _attraction("Fort", duration="1 hours", coords=(15.49, 73.82)),
        _attraction("Beach", duration="1 hours", coords=(15.30, 74.00)),
    ]

    with patch(
        "agents.itinerary_agent.matrix_distances",
        return_value=[{"status": "OK", "distance_km": 30.0, "duration_h": 0.75}],
    ):
        schedule = agent.create_schedule(
            attractions=attractions, days=1, trip_type="adventure", destination="X", restaurants=[],
            accommodation_location=None,
        )

    day = schedule["itinerary"][0]
    activities = [a for a in day["activities"] if a["type"] == "attraction"]
    assert activities[1].get("travel_time_before_minutes") == 45


def test_estimated_times_are_tagged_and_not_claimed_as_bookings():
    agent = _agent()
    attractions = [_attraction("Only one")]

    schedule = agent.create_schedule(
        attractions=attractions, days=1, trip_type="relaxation", destination="X", restaurants=[],
        accommodation_location=None,
    )

    activity = schedule["itinerary"][0]["activities"][0]
    assert activity["time_source"] == "estimated"
    assert activity["booking_status"] == "not_booked"
    assert activity["scheduling_status"] == "ok"


def test_late_start_is_flagged_as_a_scheduling_conflict_not_hidden():
    agent = _agent()
    # Each activity is long enough that the later ones push past the 21:00 cutoff.
    attractions = [_attraction(f"Long activity {i}", duration="4 hours") for i in range(4)]

    schedule = agent.create_schedule(
        attractions=attractions, days=1, trip_type="historic", destination="X", restaurants=[],
        accommodation_location=None,
    )

    activities = schedule["itinerary"][0]["activities"]
    assert any(a["scheduling_status"] == "conflict" for a in activities)
    assert any("scheduling conflict" in w for w in schedule["itinerary"][0].get("warnings", []))


def test_overloaded_day_is_flagged_rather_than_silently_crammed_in():
    agent = _agent()
    attractions = [_attraction(f"Stop {i}", duration="1 hours") for i in range(8)]

    schedule = agent.create_schedule(
        attractions=attractions, days=1, trip_type="cultural", destination="X", restaurants=[],
        accommodation_location=None,
    )

    day_warnings = schedule["itinerary"][0].get("warnings", [])
    assert any("more than comfortably fits" in w for w in day_warnings)


def test_multi_day_trip_schedules_each_day_independently():
    agent = _agent()
    attractions = [_attraction(f"Day attraction {i}") for i in range(4)]

    schedule = agent.create_schedule(
        attractions=attractions, days=2, trip_type="relaxation", destination="X", restaurants=[],
        accommodation_location=None,
    )

    assert len(schedule["itinerary"]) == 2
    for day in schedule["itinerary"]:
        times = [a["time"] for a in day["activities"] if a["type"] == "attraction"]
        assert len(set(times)) == len(times)
        if times:
            assert times[0] == "09:00"  # each day restarts at the configured day-start


def test_dining_is_still_integrated_when_data_is_available():
    """The fix must not break the pre-existing, correctly-working case where
    restaurants + accommodation_location ARE available."""
    agent = _agent()
    attractions = [
        _attraction("Morning Walk", duration="2 hours", coords=(15.49, 73.82)),
        _attraction("Afternoon Tour", duration="2 hours", coords=(15.50, 73.83)),
    ]
    restaurants = [{"name": "Beach Shack", "meal_type": "lunch", "coordinates": {"lat": 15.49, "lng": 73.82}}]

    with patch(
        "agents.itinerary_agent.matrix_distances",
        return_value=[{"status": "OK", "distance_km": 1.0, "duration_h": 0.05}],
    ):
        schedule = agent.create_schedule(
            attractions=attractions,
            days=1,
            trip_type="foodie",
            destination="X",
            restaurants=restaurants,
            accommodation_location=(15.49, 73.82),
        )

    day = schedule["itinerary"][0]
    assert day["total_meals"] >= 1
    meal = next(a for a in day["activities"] if a["type"] == "meal")
    assert meal["time_source"] == "estimated"
    assert meal["booking_status"] == "not_booked"
