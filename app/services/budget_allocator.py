"""
Deterministic budget allocation engine (Phase 11: budget-aware flight &
transportation recommendations).

Pure arithmetic - no LLM involved. Takes the trip's total budget target and
splits whatever is left after already-committed spend (confirmed bookings +
logged expenses, both real user-entered data - see app/api.py's booking/
expense endpoints) across the usual trip categories, using weights that vary
by the trip's budget level. If the user has set a hard ceiling on the flight
or transport category independently of the overall budget, that ceiling is
respected and the excess it frees up is redistributed to the other
categories rather than silently disappearing.

This produces an ESTIMATED allocation - a planning guide, not a forecast of
what will actually be spent, and never a substitute for the real committed
total (TripBudget.tsx's existing "confirmed bookings + logged expenses"
figure, which this module also uses as its "committed" input).
"""
from typing import Dict, Optional

CATEGORIES = ["flights", "accommodation", "transport", "food", "activities", "misc"]

# Weights per existing budget level (app/schemas.py's BUDGET_LEVELS). A
# "budget" trip assumes more of the spend goes to necessities (food,
# transport) relative to splurging on the flight/stay; "premium" shifts
# weight toward accommodation. These are starting assumptions, not measured
# data - deliberately documented as such rather than presented as fact.
_CATEGORY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "budget": {
        "flights": 0.28, "accommodation": 0.24, "transport": 0.14,
        "food": 0.20, "activities": 0.10, "misc": 0.04,
    },
    "mid-range": {
        "flights": 0.28, "accommodation": 0.32, "transport": 0.12,
        "food": 0.16, "activities": 0.09, "misc": 0.03,
    },
    "premium": {
        "flights": 0.24, "accommodation": 0.40, "transport": 0.12,
        "food": 0.14, "activities": 0.08, "misc": 0.02,
    },
}


def _weights_for(budget_level: str) -> Dict[str, float]:
    return _CATEGORY_WEIGHTS.get((budget_level or "").lower(), _CATEGORY_WEIGHTS["mid-range"])


def _apply_cap(allocation: Dict[str, float], category: str, cap: Optional[float]) -> None:
    """If `cap` is set and below the category's computed share, clamp it to
    the cap and redistribute the freed-up amount across the other categories,
    proportional to their existing shares. Mutates `allocation` in place."""
    if cap is None or allocation[category] <= cap:
        return
    excess = allocation[category] - cap
    allocation[category] = cap

    others = [c for c in allocation if c != category]
    others_total = sum(allocation[c] for c in others)
    if others_total <= 0:
        # Nothing to redistribute into - leave the excess unallocated rather
        # than dividing by zero or inventing a destination for it.
        return
    for c in others:
        allocation[c] += excess * (allocation[c] / others_total)


def allocate_budget(
    total_budget: float,
    budget_level: str,
    days: int,
    traveler_count: int = 1,
    committed_amount: float = 0.0,
    max_flight_budget: Optional[float] = None,
    max_transport_budget: Optional[float] = None,
) -> Dict:
    """Returns a category-by-category estimated allocation of what's left of
    `total_budget` after `committed_amount`. All money fields are in the
    trip's own currency/units - this module does no currency conversion."""
    traveler_count = max(1, traveler_count or 1)
    days = max(1, days or 1)

    remaining = max(total_budget - committed_amount, 0.0)
    weights = _weights_for(budget_level)
    allocation = {cat: round(remaining * weights[cat], 2) for cat in CATEGORIES}

    capped_categories = []
    if max_flight_budget is not None and allocation["flights"] > max_flight_budget:
        _apply_cap(allocation, "flights", max_flight_budget)
        capped_categories.append("flights")
    if max_transport_budget is not None and allocation["transport"] > max_transport_budget:
        _apply_cap(allocation, "transport", max_transport_budget)
        capped_categories.append("transport")

    allocation = {cat: round(amount, 2) for cat, amount in allocation.items()}

    return {
        "total_budget": round(total_budget, 2),
        "committed_amount": round(committed_amount, 2),
        "remaining_after_committed": round(remaining, 2),
        "budget_level": budget_level,
        "traveler_count": traveler_count,
        "days": days,
        "allocation": allocation,
        "per_traveler": {cat: round(amount / traveler_count, 2) for cat, amount in allocation.items()},
        "per_day": {cat: round(amount / days, 2) for cat, amount in allocation.items()},
        "capped_categories": capped_categories,
        "basis": "estimated",  # never "actual" - this is a planning split, not real spend
    }
