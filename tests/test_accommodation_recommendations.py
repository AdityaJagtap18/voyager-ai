from services.accommodation_recommendations import recommend_accommodations


def _acc(price_raw, rating="8.0/10", distance_km=1.0, currency="USD", source="real"):
    return {
        "name": "Test Hotel", "price_raw": price_raw, "currency": currency,
        "rating": rating, "avg_distance_to_attractions": distance_km, "source": source,
    }


def test_no_accommodations_returns_none():
    assert recommend_accommodations([]) is None
    assert recommend_accommodations(None) is None


def test_only_llm_accommodations_returns_none():
    accs = [{"name": "AI Villa", "source": "llm"}]
    assert recommend_accommodations(accs) is None


def test_llm_accommodations_are_never_scored():
    accs = [_acc(100), {"name": "AI Villa", "source": "llm"}]
    result = recommend_accommodations(accs)
    assert len(result["offers"]) == 1
    assert result["offers"][0]["index"] == 0


def test_single_real_accommodation_wins_every_category():
    result = recommend_accommodations([_acc(100)])
    assert all(idx == 0 for idx in result["recommended"].values())


def test_cheapest_and_highest_rated_can_differ():
    accs = [
        _acc(50, rating="6.0/10"),   # cheap but lower rated
        _acc(200, rating="9.5/10"),  # pricier but highly rated
    ]
    result = recommend_accommodations(accs)
    assert result["recommended"]["cheapest"] == 0
    assert result["recommended"]["highest_rated"] == 1


def test_most_central_prefers_shorter_distance():
    accs = [
        _acc(100, distance_km=5.0),
        _acc(110, distance_km=0.5),
    ]
    result = recommend_accommodations(accs)
    assert result["recommended"]["most_central"] == 1


def test_total_price_multiplies_by_nights():
    result = recommend_accommodations([_acc(100)], nights=4)
    assert result["offers"][0]["total_price"] == 400
    assert any("nights (4)" in a for a in result["assumptions"])


def test_over_budget_excluded_from_recommendations_when_alternatives_exist():
    accs = [
        _acc(50, rating="4.0/10"),
        _acc(500, rating="9.0/10"),
    ]
    result = recommend_accommodations(accs, max_nightly_budget=100)
    assert result["any_in_budget"] is True
    # Only the in-budget listing should be eligible for every category.
    assert all(idx == 0 for idx in result["recommended"].values())


def test_unparseable_rating_is_excluded_from_rating_based_recommendations():
    accs = [_acc(100, rating="N/A"), _acc(150, rating="8.0/10")]
    result = recommend_accommodations(accs)
    assert result["recommended"]["highest_rated"] == 1
