from services.flight_recommendations import recommend_flights


def _offer(price, duration_minutes, stops, departure="2026-12-15T10:00:00", currency="USD"):
    return {
        "price_raw": price, "currency": currency, "duration_minutes": duration_minutes,
        "stops": stops, "departure": departure, "arrival": None, "airline": "Test Air",
        "origin": "BOM", "destination": "GOI",
    }


def test_no_offers_returns_none():
    assert recommend_flights([]) is None


def test_single_offer_wins_every_category():
    result = recommend_flights([_offer(100, 120, 0)])
    assert all(idx == 0 for idx in result["recommended"].values())


def test_cheapest_and_fastest_can_differ():
    offers = [
        _offer(100, 300, 1),  # cheap but slow
        _offer(300, 90, 0),   # fast but expensive
    ]
    result = recommend_flights(offers)
    assert result["recommended"]["cheapest"] == 0
    assert result["recommended"]["fastest"] == 1


def test_total_price_multiplies_by_traveler_count():
    offers = [_offer(100, 120, 0)]
    result = recommend_flights(offers, traveler_count=3)
    assert result["offers"][0]["total_price"] == 300
    assert any("traveler_count (3)" in a for a in result["assumptions"])


def test_most_convenient_prefers_fewer_stops():
    offers = [
        _offer(100, 300, 2),
        _offer(110, 310, 0),
    ]
    result = recommend_flights(offers)
    assert result["recommended"]["most_convenient"] == 1


def test_best_value_prefers_lower_price_per_hour():
    offers = [
        _offer(600, 60, 0),   # 600/hr - expensive for a short hop
        _offer(300, 180, 0),  # 100/hr
    ]
    result = recommend_flights(offers)
    assert result["recommended"]["best_value"] == 1


def test_over_budget_offers_are_excluded_from_recommendations_when_alternatives_exist():
    offers = [
        _offer(50, 600, 3),    # cheapest overall but way over budget once scaled... (single traveler here, so just test flag)
        _offer(5000, 120, 0),  # clearly over any reasonable cap
    ]
    result = recommend_flights(offers, traveler_count=1, max_flight_budget=1000)
    assert result["offers"][0]["within_budget"] is True
    assert result["offers"][1]["within_budget"] is False
    # best_overall must never be the over-budget offer while an in-budget one exists
    assert result["recommended"]["best_overall"] != 1


def test_any_in_budget_false_when_every_offer_exceeds_the_cap():
    offers = [_offer(5000, 120, 0), _offer(6000, 200, 1)]
    result = recommend_flights(offers, max_flight_budget=100)
    assert result["any_in_budget"] is False
    # Still returns a full recommendation set rather than nothing - just flagged.
    assert result["recommended"]["cheapest"] is not None


def test_reasons_never_claim_savings_that_do_not_exist():
    offers = [
        _offer(100, 120, 0),  # cheapest AND fastest - nothing for others to "beat"
    ]
    result = recommend_flights(offers)
    for tag in ["fastest", "best_value", "most_convenient", "best_overall"]:
        assert "also the cheapest" in result["reasons"][tag].lower()


def test_reason_mentions_real_price_and_time_deltas():
    offers = [
        _offer(1000, 480, 1),   # cheapest, slow, one stop
        _offer(1200, 240, 0),   # pricier, fast, nonstop
    ]
    result = recommend_flights(offers)
    fastest_idx = result["recommended"]["fastest"]
    assert fastest_idx == 1
    reason = result["reasons"]["fastest"]
    assert "200" in reason  # price difference
    assert "4.0h" in reason  # time saved (480-240=240min=4h)


def test_missing_price_data_does_not_crash_scoring():
    offers = [
        {"price_raw": None, "currency": "USD", "duration_minutes": 120, "stops": 0, "departure": None, "arrival": None},
        _offer(200, 150, 1),
    ]
    result = recommend_flights(offers)
    assert result is not None
    assert result["offers"][0]["total_price"] is None


def test_weights_are_configurable():
    offers = [
        _offer(100, 600, 0),   # cheap, slow
        _offer(500, 60, 0),    # expensive, fast
    ]
    price_heavy = recommend_flights(offers, weights={"price": 0.9, "duration": 0.05, "stops": 0.05})
    duration_heavy = recommend_flights(offers, weights={"price": 0.05, "duration": 0.9, "stops": 0.05})
    assert price_heavy["recommended"]["best_overall"] == 0
    assert duration_heavy["recommended"]["best_overall"] == 1
