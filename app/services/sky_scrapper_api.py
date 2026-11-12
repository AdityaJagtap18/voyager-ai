# app/services/sky_scrapper_api.py
"""
Alternative real flight search, via the "Sky Scrapper" API on RapidAPI
(apiheya/sky-scrapper, host sky-scrapper.p.rapidapi.com).

This exists as a fallback behind services/flights_api.py's primary
"flights-sky" provider: search_flights_for_trip() there tries flights-sky
first, and only calls into this module when that path has nothing - wrong
provider configured, rate-limited/quota-exceeded, or genuinely no offers.
Both modules return the exact same offer shape so callers never need to
care which one actually answered.

Deliberately reuses RAPIDAPI_KEY rather than a separate credential: it's a
different API product on the same RapidAPI marketplace account, metered on
its own free quota independent of flights-sky's. Subscribing to its free
Basic plan (rapidapi.com/apiheya/api/sky-scrapper) is all that's needed -
no new signup/approval flow, unlike the Amadeus/Kiwi paths this replaced
(both shut their self-service developer programs; see
docs/VOYAGER_IMPLEMENTATION_AUDIT.md Phase 11l).
"""
import os
from typing import Optional

import requests

from utils.logger import logger

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
HOST = "sky-scrapper.p.rapidapi.com"
BASE_URL = f"https://{HOST}"


class SkyScrapperAPIError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(RAPIDAPI_KEY)


def _headers() -> dict:
    if not RAPIDAPI_KEY:
        raise SkyScrapperAPIError("RAPIDAPI_KEY not set")
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": HOST}


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/{path}", headers=_headers(), params=params, timeout=30)
    except requests.RequestException as exc:
        raise SkyScrapperAPIError(f"Request to {path} failed: {exc}")
    if r.status_code >= 400:
        raise SkyScrapperAPIError(f"{path} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def search_airport(query: str) -> list:
    """Resolve a free-text place name to the skyId/entityId codes the
    search endpoint needs. Returns [{title, sky_id, entity_id}]."""
    data = _get("api/v1/flights/searchAirport", {"query": query, "locale": "en-US"})
    results = []
    for entry in data.get("data") or []:
        presentation = entry.get("presentation", {})
        navigation = entry.get("navigation", {})
        results.append(
            {
                "title": presentation.get("title") or presentation.get("suggestionTitle"),
                "sky_id": navigation.get("relevantFlightParams", {}).get("skyId") or entry.get("skyId"),
                "entity_id": navigation.get("relevantFlightParams", {}).get("entityId") or entry.get("entityId"),
            }
        )
    return results


def _search_flights(
    origin_sky_id: str, dest_sky_id: str, origin_entity_id: str, dest_entity_id: str, depart_date: str
) -> list:
    """Returns a flat list of flight offers, each:
    {price, price_raw, currency, airline, duration_minutes, stops,
     origin, destination, departure, arrival}."""
    data = _get(
        "api/v1/flights/searchFlights",
        {
            "originSkyId": origin_sky_id,
            "destinationSkyId": dest_sky_id,
            "originEntityId": origin_entity_id,
            "destinationEntityId": dest_entity_id,
            "date": depart_date,
            "cabinClass": "economy",
            "adults": 1,
            "currency": "USD",
            "market": "en-US",
        },
    )
    itineraries = (data.get("data") or {}).get("itineraries") or []

    offers = []
    for item in itineraries:
        legs = item.get("legs") or []
        if not legs:
            continue
        leg = legs[0]
        marketing = (leg.get("carriers") or {}).get("marketing") or []
        price = item.get("price") or {}
        offers.append(
            {
                "price": price.get("formatted"),
                "price_raw": price.get("raw"),
                "currency": "USD",
                "airline": marketing[0]["name"] if marketing else None,
                "duration_minutes": leg.get("durationInMinutes"),
                "stops": leg.get("stopCount"),
                "origin": (leg.get("origin") or {}).get("displayCode"),
                "destination": (leg.get("destination") or {}).get("displayCode"),
                "departure": leg.get("departure"),
                "arrival": leg.get("arrival"),
            }
        )
    return offers


def search_flights_for_trip(
    origin_query: str, destination_query: str, depart_date: str, limit: int = 5
) -> Optional[list]:
    """Same contract as flights_api.search_flights_for_trip(): returns None
    (never a fabricated list) when real data isn't available for any
    reason - unconfigured, a place can't be resolved, no offers, or a
    provider error."""
    if not is_configured():
        return None
    try:
        origin_matches = search_airport(origin_query)
        if not origin_matches or not origin_matches[0]["sky_id"]:
            logger.warning(f"Real flights (Sky Scrapper): no airport match for origin '{origin_query}', skipping")
            return None
        dest_matches = search_airport(destination_query)
        if not dest_matches or not dest_matches[0]["sky_id"]:
            logger.warning(f"Real flights (Sky Scrapper): no airport match for destination '{destination_query}', skipping")
            return None

        offers = _search_flights(
            origin_matches[0]["sky_id"],
            dest_matches[0]["sky_id"],
            origin_matches[0]["entity_id"],
            dest_matches[0]["entity_id"],
            depart_date,
        )
        if not offers:
            logger.warning(
                f"Real flights (Sky Scrapper): no offers for {origin_matches[0]['sky_id']} -> "
                f"{dest_matches[0]['sky_id']} on {depart_date}"
            )
            return None

        for offer in offers:
            offer["source"] = "real"
            offer["origin_query"] = origin_matches[0]["title"] or origin_query
            offer["destination_query"] = dest_matches[0]["title"] or destination_query
        return offers[:limit]
    except SkyScrapperAPIError as exc:
        logger.warning(f"Real flights (Sky Scrapper) lookup failed: {exc}")
        return None
