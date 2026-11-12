"""
Deterministic accommodation recommendation engine (Phase 11g), mirroring
services/flight_recommendations.py's design.

Scores only the real, provider-sourced accommodations already fetched by
AccommodationAgent._get_real_hotels() (each tagged "source": "real", with a
numeric price_raw/currency and rating straight from Booking.com) into named
recommendation categories. LLM-suggested accommodations (source "llm") have
no real numeric price and are never scored or recommended - nothing here
invents a price, rating, or distance.
"""
from typing import Dict, List, Optional

DEFAULT_WEIGHTS = {"price": 0.4, "rating": 0.3, "distance": 0.3}

# Mirrors flight_recommendations._OVER_BUDGET_PENALTY: large enough that an
# over-budget option never wins the composite score while an in-budget one exists.
_OVER_BUDGET_PENALTY = 10.0

RECOMMENDATION_LABELS = {
    "cheapest": "Cheapest",
    "highest_rated": "Highest Rated",
    "most_central": "Most Central",
    "best_value": "Best Value",
    "best_overall": "Best Overall",
}


def _normalize(values: List[float]) -> List[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _parse_rating(rating: Optional[str]) -> Optional[float]:
    """Parses the "7.8/10" strings AccommodationAgent produces for real
    listings. Returns None for anything else (e.g. "N/A") rather than guessing."""
    if not rating or "/" not in rating:
        return None
    try:
        value, scale = rating.split("/", 1)
        value, scale = float(value), float(scale)
        return (value / scale) * 10 if scale else None
    except ValueError:
        return None


def recommend_accommodations(
    accommodations: Optional[List[Dict]],
    nights: int = 1,
    max_nightly_budget: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Optional[Dict]:
    """Returns None when there are no real, priced accommodations to score -
    never a fabricated recommendation for LLM-suggested lodging."""
    if not accommodations:
        return None

    real = [(i, a) for i, a in enumerate(accommodations) if a.get("source") == "real" and a.get("price_raw") is not None]
    if not real:
        return None

    nights = max(1, nights or 1)
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    scored = []
    for i, a in real:
        price_raw = a["price_raw"]
        total_price = round(price_raw * nights, 2)
        within_budget = True if max_nightly_budget is None else price_raw <= max_nightly_budget
        rating = _parse_rating(a.get("rating"))
        distance_km = a.get("avg_distance_to_attractions")

        scored.append({
            "index": i,
            "price_per_night": price_raw,
            "total_price": total_price,
            "within_budget": within_budget,
            "rating": rating,
            "distance_km": distance_km,
            "value_score": round(rating / price_raw, 4) if rating is not None and price_raw else None,
        })

    def _best_by(key, candidates, reverse=False):
        valid = [s for s in candidates if s[key] is not None]
        if not valid:
            return None
        return (max if reverse else min)(valid, key=lambda s: s[key])["index"]

    in_budget = [s for s in scored if s["within_budget"]]
    pool = in_budget if in_budget else scored

    cheapest_idx = _best_by("price_per_night", pool)
    highest_rated_idx = _best_by("rating", pool, reverse=True)
    most_central_idx = _best_by("distance_km", pool)
    best_value_idx = _best_by("value_score", pool, reverse=True)

    prices = [s["price_per_night"] for s in scored]
    ratings = [s["rating"] if s["rating"] is not None else 0.0 for s in scored]
    distances = [s["distance_km"] if s["distance_km"] is not None else 0.0 for s in scored]
    norm_price = _normalize(prices)
    norm_rating = _normalize(ratings)
    norm_distance = _normalize(distances)

    best_overall_idx = None
    best_overall_score = None
    for s, np_, nr, nd in zip(scored, norm_price, norm_rating, norm_distance):
        # Higher rating is better, so it subtracts from the score; price and
        # distance are both "lower is better", so they add.
        score = w["price"] * np_ + w["distance"] * nd - w["rating"] * nr
        if not s["within_budget"]:
            score += _OVER_BUDGET_PENALTY
        s["composite_score"] = round(score, 4)
        if best_overall_score is None or score < best_overall_score:
            best_overall_score = score
            best_overall_idx = s["index"]

    recommended = {
        "cheapest": cheapest_idx,
        "highest_rated": highest_rated_idx,
        "most_central": most_central_idx,
        "best_value": best_value_idx,
        "best_overall": best_overall_idx,
    }

    reasons = _build_reasons(accommodations, scored, recommended)

    return {
        "offers": scored,
        "recommended": recommended,
        "labels": RECOMMENDATION_LABELS,
        "reasons": reasons,
        "weights": w,
        "nights": nights,
        "max_nightly_budget": max_nightly_budget,
        "any_in_budget": bool(in_budget),
        "assumptions": [
            f"total_price multiplies the provider's nightly rate by nights ({nights}).",
            "Only real, provider-priced listings are scored - AI-suggested accommodations "
            "have no real numeric price and are never scored or recommended.",
        ],
    }


def _build_reasons(accommodations: List[Dict], scored: List[Dict], recommended: Dict[str, Optional[int]]) -> Dict[str, str]:
    reasons: Dict[str, str] = {}
    cheapest_idx = recommended.get("cheapest")
    cheapest = next((s for s in scored if s["index"] == cheapest_idx), None) if cheapest_idx is not None else None
    currency = (accommodations[cheapest_idx].get("currency") if cheapest_idx is not None else None) or ""

    by_index = {s["index"]: s for s in scored}

    for tag, idx in recommended.items():
        if idx is None:
            continue
        if tag == "cheapest":
            reasons[tag] = "The lowest price per night among the real listings found."
            continue
        s = by_index[idx]
        if cheapest is None or idx == cheapest_idx:
            reasons[tag] = "Also the cheapest option available."
            continue

        parts = []
        if s["price_per_night"] is not None and cheapest["price_per_night"] is not None:
            diff = round(s["price_per_night"] - cheapest["price_per_night"], 2)
            if diff > 0:
                parts.append(f"costs {currency}{diff:g} more per night than the cheapest option")
            elif diff < 0:
                parts.append(f"is actually {currency}{abs(diff):g} cheaper per night than the baseline cheapest listing")

        if s["rating"] is not None and cheapest["rating"] is not None:
            rating_diff = round(s["rating"] - cheapest["rating"], 1)
            if rating_diff > 0:
                parts.append(f"rates {rating_diff:g} points higher")

        if s["distance_km"] is not None and cheapest["distance_km"] is not None and s["distance_km"] < cheapest["distance_km"]:
            parts.append(f"is {round(cheapest['distance_km'] - s['distance_km'], 1):g}km closer to the attractions")

        parts = [p for p in parts if p]
        if parts:
            reasons[tag] = ("Recommended because it " + ", and ".join(parts) + ".").replace(", and .", ".")
        else:
            reasons[tag] = f"Selected as the {RECOMMENDATION_LABELS.get(tag, tag)} option for this search."

    return reasons
