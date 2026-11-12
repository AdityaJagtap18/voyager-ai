"""
Deterministic transportation recommendation engine (Phase 11b).

Real-data constraint: no rental-car, taxi/rideshare, or public-transit
pricing/availability provider is integrated anywhere in this codebase. The
only real transportation data that exists is distance/duration from
OpenRouteService (ORS) routing, already computed by two other agents:

  1. TransportAgent.find_airport_transfer() - a real driving route from the
     destination's airport to the trip's accommodation.
  2. ItineraryAgent - real driving-profile distances between consecutive
     scheduled stops within a day, attached to each activity as
     `travel_after: {distance_km, duration_h}` when both stops have
     coordinates.

This module never fabricates a fare, a live transit ETA, or availability.
It only classifies a recommended *mode* (walk / cycle / taxi-or-transit /
dedicated transfer) from real distance, and explains that classification
with the real numbers behind it - the same "deterministic score, no invented
price" discipline used in budget_allocator.py and flight_recommendations.py.

"Intercity transport" (train/bus between multiple cities within one trip)
is intentionally out of scope: this app models a trip as a single
destination, so there is no second city to transfer to - it isn't a
provider gap, it's a mismatch with the app's current data model.
"""
from typing import Any, Dict, List, Optional

# (max_km_inclusive, mode, reason) - checked in order, first match wins.
_MODE_THRESHOLDS_KM = [
    (1.2, "walk", "Short enough to walk - no vehicle needed."),
    (6.0, "cycle", "A comfortable cycling distance - a bike or e-scooter rental works well here."),
    (20.0, "taxi_or_transit", "Too far to walk or cycle comfortably - take a taxi, rideshare, or local public transit."),
]
_DEFAULT_MODE = "dedicated_transfer"
_DEFAULT_REASON = "This is a long hop - plan a dedicated transfer (taxi, rideshare, or intercity transport)."


def classify_distance(distance_km: Optional[float]) -> Optional[Dict[str, str]]:
    """Maps a real distance to a recommended mode + human-readable reason.
    Returns None for missing/invalid distance - never guesses a mode without one."""
    if distance_km is None or distance_km < 0:
        return None
    for max_km, mode, reason in _MODE_THRESHOLDS_KM:
        if distance_km <= max_km:
            return {"recommended_mode": mode, "reason": reason}
    return {"recommended_mode": _DEFAULT_MODE, "reason": _DEFAULT_REASON}


def recommend_airport_transfer(transportation: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Adds a deterministic mode recommendation to the existing real airport
    transfer route. Returns None unchanged when there's no real transfer to
    annotate - never invents one."""
    if not transportation or transportation.get("distance_km") is None:
        return None
    classification = classify_distance(transportation["distance_km"])
    if classification is None:
        return None
    # An airport transfer is never realistically "walk" or "cycle" - collapse
    # those into the taxi/transit tier rather than suggesting someone walk an
    # airport-to-hotel distance that merely happened to be short on the map.
    mode = classification["recommended_mode"]
    if mode in ("walk", "cycle"):
        mode = "taxi_or_transit"
    reason = (
        "A short, real driving transfer - taxi, rideshare, or an airport shuttle are all "
        "reasonable for this distance."
        if mode == "taxi_or_transit"
        else classification["reason"]
    )
    return {
        **transportation,
        "recommended_mode": mode,
        "reason": reason,
    }


def recommend_local_transport(itinerary_days: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Walks each day's real inter-stop hops (attached by ItineraryAgent as
    `travel_after` on an activity once both stops have coordinates) and
    returns one mode recommendation per real hop found. Returns [] when
    there's no real hop data at all - nothing is fabricated to fill the gap."""
    hops: List[Dict[str, Any]] = []
    for day in itinerary_days or []:
        day_num = day.get("day")
        activities = day.get("activities") or []
        for i, activity in enumerate(activities):
            travel_after = activity.get("travel_after")
            if not travel_after or travel_after.get("distance_km") is None:
                continue
            classification = classify_distance(travel_after["distance_km"])
            if classification is None:
                continue
            next_activity = activities[i + 1] if i + 1 < len(activities) else None
            hops.append({
                "day": day_num,
                "from": activity.get("name"),
                "to": next_activity.get("name") if next_activity else None,
                "distance_km": travel_after["distance_km"],
                "duration_h": travel_after.get("duration_h"),
                "recommended_mode": classification["recommended_mode"],
                "reason": classification["reason"],
                "source": "real",
            })
    return hops


def recommend_transport(
    transportation: Optional[Dict[str, Any]],
    itinerary_days: Optional[List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """Combines the airport-transfer and local-transport recommendations
    into one response. Returns None when there's nothing real to recommend
    on at all (no airport transfer and no routed inter-stop hops)."""
    airport_transfer = recommend_airport_transfer(transportation)
    local_transport = recommend_local_transport(itinerary_days)
    if airport_transfer is None and not local_transport:
        return None
    return {
        "airport_transfer": airport_transfer,
        "local_transport": local_transport,
        "intercity_transport": None,
        "assumptions": [
            "No rental-car, taxi/rideshare, or public-transit pricing or availability provider is "
            "integrated - every recommendation here is a mode classification from real routed "
            "distance only, never a fare, live ETA, or invented availability.",
            "Intercity transport is not modeled: this app plans a single-destination trip, so there "
            "is no second city to route between.",
        ],
    }
