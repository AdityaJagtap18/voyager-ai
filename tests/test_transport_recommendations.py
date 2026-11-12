from services.transport_recommendations import (
    classify_distance,
    recommend_airport_transfer,
    recommend_local_transport,
    recommend_transport,
)


def test_classify_distance_none_returns_none():
    assert classify_distance(None) is None


def test_classify_distance_negative_returns_none():
    assert classify_distance(-1) is None


def test_classify_distance_walk_tier():
    result = classify_distance(0.8)
    assert result["recommended_mode"] == "walk"


def test_classify_distance_cycle_tier():
    result = classify_distance(4.0)
    assert result["recommended_mode"] == "cycle"


def test_classify_distance_taxi_or_transit_tier():
    result = classify_distance(15.0)
    assert result["recommended_mode"] == "taxi_or_transit"


def test_classify_distance_dedicated_transfer_tier():
    result = classify_distance(45.0)
    assert result["recommended_mode"] == "dedicated_transfer"


def test_airport_transfer_none_when_no_transportation():
    assert recommend_airport_transfer(None) is None


def test_airport_transfer_none_when_distance_missing():
    assert recommend_airport_transfer({"mode": "driving", "distance_km": None}) is None


def test_airport_transfer_collapses_short_distance_to_taxi_or_transit():
    transfer = {"mode": "driving", "distance_km": 0.9, "duration_h": 0.1, "from": "Airport", "to": "accommodation"}
    result = recommend_airport_transfer(transfer)
    assert result["recommended_mode"] == "taxi_or_transit"
    assert result["distance_km"] == 0.9  # original real fields preserved


def test_airport_transfer_long_distance_gets_dedicated_transfer():
    transfer = {"mode": "driving", "distance_km": 40.0, "duration_h": 1.0, "from": "Airport", "to": "accommodation"}
    result = recommend_airport_transfer(transfer)
    assert result["recommended_mode"] == "dedicated_transfer"


def test_airport_transfer_never_fabricates_a_price():
    transfer = {"mode": "driving", "distance_km": 10.0, "duration_h": 0.3, "from": "Airport", "to": "accommodation"}
    result = recommend_airport_transfer(transfer)
    assert "price" not in result
    assert "fare" not in result
    assert "cost" not in result


def test_local_transport_empty_for_no_days():
    assert recommend_local_transport(None) == []
    assert recommend_local_transport([]) == []


def test_local_transport_skips_activities_without_travel_after():
    days = [{"day": 1, "activities": [{"name": "Beach"}, {"name": "Museum"}]}]
    assert recommend_local_transport(days) == []


def test_local_transport_extracts_real_hops_only():
    days = [{
        "day": 1,
        "activities": [
            {"name": "Beach", "travel_after": {"distance_km": 2.0, "duration_h": 0.1}},
            {"name": "Museum", "travel_after": {"distance_km": 30.0, "duration_h": 0.8}},
            {"name": "Market"},
        ],
    }]
    hops = recommend_local_transport(days)
    assert len(hops) == 2
    assert hops[0] == {
        "day": 1, "from": "Beach", "to": "Museum", "distance_km": 2.0, "duration_h": 0.1,
        "recommended_mode": "cycle", "reason": hops[0]["reason"], "source": "real",
    }
    assert hops[1]["from"] == "Museum"
    assert hops[1]["to"] == "Market"
    assert hops[1]["recommended_mode"] == "dedicated_transfer"


def test_local_transport_across_multiple_days():
    days = [
        {"day": 1, "activities": [{"name": "A", "travel_after": {"distance_km": 1.0}}, {"name": "B"}]},
        {"day": 2, "activities": [{"name": "C", "travel_after": {"distance_km": 1.0}}, {"name": "D"}]},
    ]
    hops = recommend_local_transport(days)
    assert [h["day"] for h in hops] == [1, 2]


def test_recommend_transport_none_when_nothing_real_exists():
    assert recommend_transport(None, None) is None
    assert recommend_transport(None, [{"day": 1, "activities": [{"name": "A"}]}]) is None


def test_recommend_transport_combines_both_sources():
    transfer = {"mode": "driving", "distance_km": 25.0, "duration_h": 0.5, "from": "Airport", "to": "accommodation"}
    days = [{"day": 1, "activities": [{"name": "A", "travel_after": {"distance_km": 2.0}}, {"name": "B"}]}]
    result = recommend_transport(transfer, days)
    assert result["airport_transfer"]["recommended_mode"] == "dedicated_transfer"
    assert len(result["local_transport"]) == 1
    assert result["intercity_transport"] is None
    assert len(result["assumptions"]) == 2


def test_recommend_transport_present_with_only_local_hops():
    days = [{"day": 1, "activities": [{"name": "A", "travel_after": {"distance_km": 2.0}}, {"name": "B"}]}]
    result = recommend_transport(None, days)
    assert result["airport_transfer"] is None
    assert len(result["local_transport"]) == 1
