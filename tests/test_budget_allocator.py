from services.budget_allocator import allocate_budget, CATEGORIES


def test_allocation_sums_to_remaining_after_committed():
    result = allocate_budget(
        total_budget=50000, budget_level="mid-range", days=5, traveler_count=2, committed_amount=10000,
    )
    assert result["remaining_after_committed"] == 40000
    assert abs(sum(result["allocation"].values()) - 40000) < 1.0
    assert set(result["allocation"]) == set(CATEGORIES)


def test_committed_amount_reduces_remaining_budget():
    no_commit = allocate_budget(total_budget=50000, budget_level="mid-range", days=5, committed_amount=0)
    with_commit = allocate_budget(total_budget=50000, budget_level="mid-range", days=5, committed_amount=20000)
    assert with_commit["remaining_after_committed"] == no_commit["remaining_after_committed"] - 20000
    for cat in CATEGORIES:
        assert with_commit["allocation"][cat] < no_commit["allocation"][cat]


def test_committed_amount_cannot_push_remaining_negative():
    result = allocate_budget(total_budget=10000, budget_level="budget", days=3, committed_amount=50000)
    assert result["remaining_after_committed"] == 0.0
    assert sum(result["allocation"].values()) == 0.0


def test_budget_levels_weight_accommodation_differently():
    budget = allocate_budget(total_budget=100000, budget_level="budget", days=5)
    premium = allocate_budget(total_budget=100000, budget_level="premium", days=5)
    assert premium["allocation"]["accommodation"] > budget["allocation"]["accommodation"]


def test_unknown_budget_level_falls_back_to_mid_range():
    unknown = allocate_budget(total_budget=50000, budget_level="not-a-real-level", days=5)
    mid_range = allocate_budget(total_budget=50000, budget_level="mid-range", days=5)
    assert unknown["allocation"] == mid_range["allocation"]


def test_flight_budget_cap_is_respected_and_redistributed():
    uncapped = allocate_budget(total_budget=100000, budget_level="mid-range", days=5)
    flight_share = uncapped["allocation"]["flights"]
    cap = flight_share / 2

    capped = allocate_budget(total_budget=100000, budget_level="mid-range", days=5, max_flight_budget=cap)
    assert capped["allocation"]["flights"] == round(cap, 2)
    assert "flights" in capped["capped_categories"]
    # The freed-up amount must go somewhere, not vanish.
    assert abs(sum(capped["allocation"].values()) - uncapped["allocation"]["flights"] - (
        sum(uncapped["allocation"].values()) - uncapped["allocation"]["flights"]
    )) < 1.0
    assert sum(capped["allocation"].values()) > sum(uncapped["allocation"].values()) - flight_share  # redistributed, not dropped


def test_transport_budget_cap_only_affects_transport_when_already_under_cap():
    result = allocate_budget(total_budget=50000, budget_level="mid-range", days=5, max_transport_budget=999999)
    assert result["capped_categories"] == []


def test_per_traveler_and_per_day_breakdowns_divide_correctly():
    result = allocate_budget(total_budget=60000, budget_level="mid-range", days=3, traveler_count=4)
    for cat in CATEGORIES:
        assert result["per_traveler"][cat] == round(result["allocation"][cat] / 4, 2)
        assert result["per_day"][cat] == round(result["allocation"][cat] / 3, 2)


def test_traveler_count_and_days_are_floored_at_one():
    result = allocate_budget(total_budget=10000, budget_level="budget", days=0, traveler_count=0)
    assert result["traveler_count"] == 1
    assert result["days"] == 1


def test_basis_is_always_labeled_estimated():
    result = allocate_budget(total_budget=10000, budget_level="budget", days=1)
    assert result["basis"] == "estimated"
