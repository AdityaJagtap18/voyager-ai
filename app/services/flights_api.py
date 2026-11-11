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
"""
import os
import requests

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
