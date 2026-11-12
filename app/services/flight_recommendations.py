"""
Deterministic flight recommendation engine (Phase 11: budget-aware flight &
transportation recommendations).

Takes the real flight offers already fetched by services/flights_api.py
(search_flights_for_trip - each tagged "source": "real") and scores them
into named recommendation categories. All scoring is plain arithmetic on
fields the provider actually returned; nothing here calls an LLM or invents
a price, duration, or stop count. An LLM may turn the `reason` strings this
module produces into friendlier prose elsewhere, but it never generates the
underlying numbers or the recommendation itself.

Assumption this module makes explicit rather than silently baking in: the
provider's `price_raw` is a per-traveler fare (Skyscanner-style search APIs
quote this way by default), so the total cost for the trip's travelers is
`price_raw * traveler_count`. That assumption is returned in `assumptions`
on every result so a caller can surface it instead of it being invisible.
"""
from typing import Dict, List, Optional

# Default weights for the "best overall" composite score. Lower normalized
# score wins. Configurable per call (section 6 of the spec: "make scoring
# weights configurable") - these are just the defaults.
DEFAULT_WEIGHTS = {"price": 0.45, "duration": 0.30, "stops": 0.25}

# An offer over budget is still shown (for comparison), but is never chosen
# as a recommendation unless literally every offer is over budget - this
# penalty just needs to be large enough that no in-budget offer ever loses
# to an over-budget one in the composite score.
_OVER_BUDGET_PENALTY = 10.0

RECOMMENDATION_LABELS = {
    "cheapest": "Cheapest",
    "fastest": "Fastest",
    "best_value": "Best Value",
    "most_convenient": "Most Convenient",
    "best_overall": "Best Overall",
}


def _normalize(values: List[float]) -> List[float]:
    """Min-max normalize to [0, 1]; a constant list normalizes to all 0s."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def _departure_hour(departure_iso: Optional[str]) -> Optional[float]:
    if not departure_iso or "T" not in departure_iso:
        return None
    try:
        time_part = departure_iso.split("T", 1)[1]
        h, m = time_part.split(":")[:2]
        return int(h) + int(m) / 60
    except (ValueError, IndexError):
        return None


def recommend_flights(
    offers: List[Dict],
    traveler_count: int = 1,
    max_flight_budget: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Optional[Dict]:
    """Returns None when there's nothing to score (no offers) - never a
    fabricated recommendation set. Otherwise returns per-offer totals/scores
    plus which offer index wins each named category."""
    if not offers:
        return None

    traveler_count = max(1, traveler_count or 1)
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    scored = []
    for i, offer in enumerate(offers):
        price_raw = offer.get("price_raw")
        total_price = round(price_raw * traveler_count, 2) if price_raw is not None else None
        within_budget = True if max_flight_budget is None or total_price is None else total_price <= max_flight_budget
        duration_minutes = offer.get("duration_minutes")
        stops = offer.get("stops")
        dep_hour = _departure_hour(offer.get("departure"))
        # A very early or very late departure is less convenient, independent
        # of stop count - penalize the 00:00-05:00 and 23:00-24:00 windows.
        odd_hour_penalty = 1.0 if dep_hour is not None and (dep_hour < 5 or dep_hour >= 23) else 0.0

        scored.append({
            "index": i,
            "total_price": total_price,
            "within_budget": within_budget,
            "duration_minutes": duration_minutes,
            "stops": stops,
            "odd_hour_penalty": odd_hour_penalty,
            "price_per_hour": (
                round(total_price / (duration_minutes / 60), 2)
                if total_price is not None and duration_minutes
                else None
            ),
        })

    def _best_by(key, candidates=None):
        pool = candidates if candidates is not None else scored
        valid = [s for s in pool if s[key] is not None]
        if not valid:
            return None
        return min(valid, key=lambda s: s[key])["index"]

    in_budget = [s for s in scored if s["within_budget"]]
    pool_for_recs = in_budget if in_budget else scored  # fall back to all if nothing fits

    cheapest_idx = _best_by("total_price", pool_for_recs)
    fastest_idx = _best_by("duration_minutes", pool_for_recs)
    most_convenient_idx = _best_by_convenience(scored, pool_for_recs)
    best_value_idx = _best_by("price_per_hour", pool_for_recs)

    # Composite "best overall": normalize price/duration/stops across ALL
    # offers (so the scale is meaningful), then pick the lowest weighted sum
    # among the in-budget pool, with a penalty added for being over budget
    # so an over-budget offer never wins while any in-budget offer exists.
    prices = [s["total_price"] if s["total_price"] is not None else 0.0 for s in scored]
    durations = [s["duration_minutes"] if s["duration_minutes"] is not None else 0.0 for s in scored]
    stops_list = [s["stops"] if s["stops"] is not None else 0.0 for s in scored]
    norm_price = _normalize(prices)
    norm_duration = _normalize(durations)
    norm_stops = _normalize(stops_list)

    best_overall_idx = None
    best_overall_score = None
    for s, np_, nd, ns in zip(scored, norm_price, norm_duration, norm_stops):
        score = w["price"] * np_ + w["duration"] * nd + w["stops"] * ns
        if not s["within_budget"]:
            score += _OVER_BUDGET_PENALTY
        s["composite_score"] = round(score, 4)
        if best_overall_score is None or score < best_overall_score:
            best_overall_score = score
            best_overall_idx = s["index"]

    recommended = {
        "cheapest": cheapest_idx,
        "fastest": fastest_idx,
        "best_value": best_value_idx,
        "most_convenient": most_convenient_idx,
        "best_overall": best_overall_idx,
    }

    reasons = _build_reasons(offers, scored, recommended)

    return {
        "offers": scored,
        "recommended": recommended,
        "labels": RECOMMENDATION_LABELS,
        "reasons": reasons,
        "weights": w,
        "traveler_count": traveler_count,
        "max_flight_budget": max_flight_budget,
        "any_in_budget": bool(in_budget),
        "assumptions": [
            "Each provider fare is assumed to be priced per traveler; total_price multiplies it "
            f"by traveler_count ({traveler_count}).",
            "Scores are computed only from fields the provider returned - nothing here is "
            "LLM-generated or estimated.",
        ],
    }


def _best_by_convenience(all_scored: List[Dict], pool: List[Dict]) -> Optional[int]:
    """Fewest stops first, then avoid odd departure hours, then shortest duration."""
    valid = [s for s in pool if s["stops"] is not None]
    if not valid:
        return None
    best = min(
        valid,
        key=lambda s: (
            s["stops"],
            s["odd_hour_penalty"],
            s["duration_minutes"] if s["duration_minutes"] is not None else float("inf"),
        ),
    )
    return best["index"]


def _build_reasons(offers: List[Dict], scored: List[Dict], recommended: Dict[str, Optional[int]]) -> Dict[str, str]:
    """Explanation strings built only from real numeric deltas between the
    recommended offer and the cheapest one - never asserted unless the
    numbers actually support the claim."""
    reasons: Dict[str, str] = {}
    cheapest_idx = recommended.get("cheapest")
    cheapest = scored[cheapest_idx] if cheapest_idx is not None else None
    currency = (offers[cheapest_idx].get("currency") if cheapest_idx is not None else None) or ""

    for tag, idx in recommended.items():
        if idx is None:
            continue
        if tag == "cheapest":
            reasons[tag] = "The lowest total price among the offers found for this search."
            continue
        s = scored[idx]
        if cheapest is None or idx == cheapest_idx:
            reasons[tag] = "Also the cheapest option available."
            continue

        parts = []
        if s["total_price"] is not None and cheapest["total_price"] is not None:
            diff = round(s["total_price"] - cheapest["total_price"], 2)
            if diff > 0:
                parts.append(f"costs {currency}{diff:g} more than the cheapest option")
            elif diff < 0:
                parts.append(f"is actually {currency}{abs(diff):g} cheaper than the baseline cheapest offer")

        if s["duration_minutes"] is not None and cheapest["duration_minutes"] is not None:
            minutes_saved = cheapest["duration_minutes"] - s["duration_minutes"]
            if minutes_saved > 0:
                parts.append(f"saves {minutes_saved / 60:.1f}h")
            elif minutes_saved < 0:
                parts.append(f"takes {abs(minutes_saved) / 60:.1f}h longer")

        if s["stops"] is not None and cheapest["stops"] is not None and s["stops"] < cheapest["stops"]:
            parts.append("avoids a connecting flight" if cheapest["stops"] >= 1 else "")

        parts = [p for p in parts if p]
        if parts:
            reasons[tag] = ("Recommended because it " + ", and ".join(parts) + ".").replace(", and .", ".")
        else:
            reasons[tag] = f"Selected as the {RECOMMENDATION_LABELS.get(tag, tag)} option for this search."

    return reasons
