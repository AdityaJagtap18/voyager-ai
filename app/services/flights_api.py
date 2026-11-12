# app/services/flights_api.py
"""
Real flight search (Phase 3), via the "Flights Scraper Sky" API on RapidAPI.

A separate API from app/services/hotels_api.py's Booking.com-scraper
(booking-com15.p.rapidapi.com) despite similar naming — this one
(flights-sky.p.rapidapi.com) backs onto Skyscanner-style data and returned
clean, reliable results in testing. The RapidAPI listing's own "Booking.com
Flights" section (same host, different paths) turned out to proxy booking.com
directly and hit its anti-bot captcha on a live test call — avoided here in
favor of this host's plain `/flights/*` paths, which didn't.

search_flights_for_trip() below falls back to services/sky_scrapper_api.py
(Phase 11l) when this provider has nothing - unconfigured, rate-limited, or
genuinely no offers - so a single RapidAPI free-tier quota running out
doesn't take real flight data down for the whole app. (An earlier version
of this fallback targeted Amadeus' self-service Flight Offers Search API,
but that program was decommissioned - replaced with a sales-gated
"Enterprise API Portal" - before it could be used; Sky Scrapper is a
different API product on the same RapidAPI account/key, with its own free
quota, so it needs no new signup at all.)
"""
import os
from typing import Optional
import requests

from services import sky_scrapper_api
from utils.logger import logger

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
HOST = "flights-sky.p.rapidapi.com"
BASE_URL = f"https://{HOST}"


class FlightsAPIError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(RAPIDAPI_KEY)


def _headers() -> dict:
    if not RAPIDAPI_KEY:
        raise FlightsAPIError("RAPIDAPI_KEY not set")
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": HOST}


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/{path}", headers=_headers(), params=params, timeout=30)
    except requests.RequestException as exc:
        raise FlightsAPIError(f"Request to {path} failed: {exc}")
    if r.status_code >= 400:
        raise FlightsAPIError(f"{path} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def autocomplete_place(query: str) -> list:
    """Resolve a free-text place name to the airport/city codes the search
    endpoint needs. Returns [{title, subtitle, sky_id, entity_id, type}]."""
    data = _get("flights/auto-complete", {"query": query})
    results = []
    for entry in data.get("data") or []:
        presentation = entry.get("presentation", {})
        navigation = entry.get("navigation", {})
        results.append(
            {
                "title": presentation.get("title"),
                "subtitle": presentation.get("subtitle"),
                "sky_id": presentation.get("skyId"),
                "entity_id": navigation.get("entityId"),
                "type": navigation.get("entityType"),
            }
        )
    return results


def search_one_way(origin: str, destination: str, depart_date: str, currency: str = "USD", market: str = "US") -> list:
    """origin/destination: a skyId/IATA code (from autocomplete_place or a
    known airport code like "BOM"). depart_date: "YYYY-MM-DD". Returns a flat
    list of flight offers from the API's "Best" bucket, each:
    {price, price_raw, currency, airline, duration_minutes, stops,
     origin, destination, departure, arrival}."""
    data = _get(
        "flights/search-one-way",
        {
            "fromEntityId": origin,
            "toEntityId": destination,
            "departDate": depart_date,
            "market": market,
            "locale": "en-US",
            "currency": currency,
        },
    )
    buckets = (data.get("data") or {}).get("itineraries", {}).get("buckets") or []
    items = buckets[0]["items"] if buckets else []

    offers = []
    for item in items:
        legs = item.get("legs") or []
        if not legs:
            continue
        leg = legs[0]
        marketing = (leg.get("carriers") or {}).get("marketing") or []
        offers.append(
            {
                "price": item.get("price", {}).get("formatted"),
                "price_raw": item.get("price", {}).get("raw"),
                "currency": currency,
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


def _search_via_rapidapi(origin_query: str, destination_query: str, depart_date: str, limit: int = 5) -> Optional[list]:
    """Resolves both place names via autocomplete_place() to the skyId codes
    search_one_way() needs, then searches. Returns None (never a fabricated
    list) when the provider is unconfigured, either place can't be resolved,
    no offers come back, or the provider errors."""
    if not is_configured():
        return None
    try:
        origin_matches = autocomplete_place(origin_query)
        if not origin_matches:
            logger.warning(f"Real flights (RapidAPI): no autocomplete match for origin '{origin_query}', skipping")
            return None
        dest_matches = autocomplete_place(destination_query)
        if not dest_matches:
            logger.warning(f"Real flights (RapidAPI): no autocomplete match for destination '{destination_query}', skipping")
            return None

        origin_sky_id = origin_matches[0]["sky_id"]
        dest_sky_id = dest_matches[0]["sky_id"]
        if not origin_sky_id or not dest_sky_id:
            logger.warning(f"Real flights (RapidAPI): autocomplete match for '{origin_query}' -> '{destination_query}' had no skyId, skipping")
            return None

        offers = search_one_way(origin_sky_id, dest_sky_id, depart_date)
        if not offers:
            logger.warning(f"Real flights (RapidAPI): no offers for {origin_sky_id} -> {dest_sky_id} on {depart_date}")
            return None

        for offer in offers:
            offer["source"] = "real"
            offer["origin_query"] = origin_matches[0]["title"]
            offer["destination_query"] = dest_matches[0]["title"]
        return offers[:limit]
    except FlightsAPIError as exc:
        logger.warning(f"Real flights (RapidAPI) lookup failed: {exc}")
        return None


def search_flights_for_trip(origin_query: str, destination_query: str, depart_date: str, limit: int = 5) -> Optional[list]:
    """Real flight search grounded in free-text origin/destination (Phase 10
    fusion). Tries the RapidAPI "flights-sky" provider first, then falls
    back to services/sky_scrapper_api.py (Phase 11l) if that has nothing.
    Returns None (never a fabricated list) only once both providers have
    nothing - callers must treat None as "no real flight data available"
    rather than inventing prices/times to fill the gap (per the platform's
    anti-fabrication requirements).
    """
    offers = _search_via_rapidapi(origin_query, destination_query, depart_date, limit)
    if offers:
        return offers

    sky_scrapper_configured = sky_scrapper_api.is_configured()
    if sky_scrapper_configured:
        offers = sky_scrapper_api.search_flights_for_trip(origin_query, destination_query, depart_date, limit)
        if offers:
            return offers

    if is_configured() or sky_scrapper_configured:
        logger.warning(
            f"Real flights: no offers for '{origin_query}' -> '{destination_query}' on {depart_date} from any "
            "configured provider; no flight data shown (flights have no LLM fallback, by design)"
        )
    return None
