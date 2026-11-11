# app/services/hotels_api.py
"""
Real hotel search (Phase 3), via the "Booking COM" API on RapidAPI
(booking-com15.p.rapidapi.com) — a reliable, non-scraper-blocked data source
confirmed live during development (real hotel names, prices, review scores,
coordinates for Goa, India).
"""
import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
HOST = "booking-com15.p.rapidapi.com"
BASE_URL = f"https://{HOST}"


class HotelsAPIError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(RAPIDAPI_KEY)


def _headers() -> dict:
    if not RAPIDAPI_KEY:
        raise HotelsAPIError("RAPIDAPI_KEY not set")
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": HOST}


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/{path}", headers=_headers(), params=params, timeout=30)
    except requests.RequestException as exc:
        raise HotelsAPIError(f"Request to {path} failed: {exc}")
    if r.status_code >= 400:
        raise HotelsAPIError(f"{path} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def search_destination(query: str) -> list:
    """Resolve a free-text place name to the dest_id/search_type
    search_hotels() needs. Returns [{dest_id, search_type, label, country,
    latitude, longitude}]."""
    data = _get("api/v1/hotels/searchDestination", {"query": query})
    results = []
    for entry in data.get("data") or []:
        results.append(
            {
                "dest_id": entry.get("dest_id"),
                "search_type": entry.get("search_type"),
                "label": entry.get("label"),
                "country": entry.get("country"),
                "latitude": entry.get("latitude"),
                "longitude": entry.get("longitude"),
            }
        )
    return results


def search_hotels(
    dest_id: str,
    search_type: str,
    checkin_date: str,
    checkout_date: str,
    adults: int = 2,
    room_qty: int = 1,
    currency: str = "USD",
) -> list:
    """checkin_date/checkout_date: "YYYY-MM-DD". Returns a list of hotel
    offers: {name, price_formatted, price_raw, currency, review_score,
    review_score_word, star_rating, photo_url, latitude, longitude}."""
    data = _get(
        "api/v1/hotels/searchHotels",
        {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": checkin_date,
            "departure_date": checkout_date,
            "adults": adults,
            "room_qty": room_qty,
            "page_number": 1,
            "currency_code": currency,
        },
    )
    hotels = ((data.get("data") or {}).get("hotels")) or []

    offers = []
    for entry in hotels:
        prop = entry.get("property") or {}
        gross_price = (prop.get("priceBreakdown") or {}).get("grossPrice") or {}
        photo_urls = prop.get("photoUrls") or []
        offers.append(
            {
                "hotel_id": entry.get("hotel_id"),
                "name": prop.get("name"),
                "price_formatted": gross_price.get("amountRounded"),
                "price_raw": gross_price.get("value"),
                "currency": gross_price.get("currency") or currency,
                "review_score": prop.get("reviewScore"),
                "review_score_word": prop.get("reviewScoreWord"),
                "star_rating": prop.get("accuratePropertyClass") or prop.get("propertyClass"),
                "photo_url": photo_urls[0] if photo_urls else None,
                "latitude": prop.get("latitude"),
                "longitude": prop.get("longitude"),
            }
        )
    return offers
