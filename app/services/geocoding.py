# app/services/geocoding.py
"""
Shared attraction geocoding + validation.

Originally this only happened inside ItineraryAgent, as its very last step —
which meant the Accommodation and Dining agents (steps 2 and 3) always saw
attractions with no 'coordinates' key, silently skipping their own
proximity-to-attractions scoring the entire time (discovered via live
testing of the dining real-data fusion: real restaurant coordinates were
correct, but got compared against an arbitrary, unscored "best"
accommodation instead of the actual closest one). Calling this right after
the Research step — before Accommodation/Dining run — fixes that for both
orchestrators (app/workflow.py, app/orchestration/crewai_adapter.py).

ItineraryAgent still calls its own copy of this logic too (for callers that
skip the earlier step, e.g. existing tests) but skips attractions that
already carry a 'coordinates' key, so there's no duplicate geocoding when
both steps run.
"""
from math import radians, cos, sin, asin, sqrt
from typing import Dict, List, Tuple

from services.ors_api import geocode, ORSError
from utils.logger import logger

MAX_REASONABLE_DISTANCE_KM = 50


def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Great-circle distance between two (lat, lng) points, in km."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * 6371


def geocode_attractions(attractions: List[Dict], destination: str) -> List[Dict]:
    """Add real coordinates to attractions that don't already have one (skips
    any that do, so calling this twice in a row is cheap), then drop any
    whose geocoded point lands implausibly far from the destination's own
    center (a frequent ORS false-match for ambiguous/common attraction
    names, e.g. a same-named place in another city)."""
    to_geocode = [a for a in attractions if "coordinates" not in a]
    if to_geocode:
        logger.info("Geocoding attractions for distance calculations")

    for attraction in to_geocode:
        query = f"{attraction['name']}, {destination}"
        try:
            coords = geocode(query, limit=1)
            if coords:
                attraction["coordinates"] = {"lat": coords[0][0], "lng": coords[0][1]}
            else:
                attraction["coordinates"] = None
                logger.warning(f"  Could not geocode: {attraction['name']}")
        except ORSError as e:
            logger.warning(f"  Geocoding failed for {attraction['name']}: {e}")
            attraction["coordinates"] = None

    if not to_geocode:
        return attractions

    try:
        center_coords = geocode(destination, limit=1)
    except ORSError as e:
        logger.warning(f"Could not geocode destination center, skipping validation: {e}")
        return attractions

    if not center_coords:
        logger.warning("Could not geocode destination center, skipping validation")
        return attractions

    center = center_coords[0]
    for attraction in to_geocode:
        if attraction.get("coordinates"):
            distance = haversine_distance(
                center, (attraction["coordinates"]["lat"], attraction["coordinates"]["lng"])
            )
            if distance > MAX_REASONABLE_DISTANCE_KM:
                logger.warning(
                    f"  {attraction['name']} geocoded {distance:.0f}km from city center - "
                    f"likely error, removing coordinates"
                )
                attraction["coordinates"] = None
                attraction["geocoding_error"] = True

    return attractions
