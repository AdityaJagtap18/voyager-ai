# app/services/restaurants_api.py
"""
Real restaurant search (dining planner fusion), via the "Local Business
Data" API on RapidAPI (local-business-data.p.rapidapi.com) — a Google
Maps-backed business search confirmed live during development (real
restaurant names, ratings, addresses, coordinates for Jaipur, India).

Unlike hotels_api.py, this provider resolves the destination from free text
embedded directly in the search query (e.g. "restaurants in Jaipur, India")
rather than needing a separate destination-lookup call first.
"""
import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
HOST = "local-business-data.p.rapidapi.com"
BASE_URL = f"https://{HOST}"


class RestaurantsAPIError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(RAPIDAPI_KEY)


def _headers() -> dict:
    if not RAPIDAPI_KEY:
        raise RestaurantsAPIError("RAPIDAPI_KEY not set")
    return {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": HOST}


def _get(path: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE_URL}/{path}", headers=_headers(), params=params, timeout=30)
    except requests.RequestException as exc:
        raise RestaurantsAPIError(f"Request to {path} failed: {exc}")
    if r.status_code >= 400:
        raise RestaurantsAPIError(f"{path} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def search_restaurants(destination: str, limit: int = 10) -> list:
    """Real restaurant listings near `destination` (free-text place name,
    e.g. "Jaipur, India"). Returns a list of {name, rating, review_count,
    price_level, address, description, types, latitude, longitude, website}."""
    data = _get("search", {"query": f"restaurants in {destination}", "limit": limit, "lang": "en"})
    results = []
    for entry in data.get("data") or []:
        about = entry.get("about") or {}
        types = entry.get("subtypes") or ([entry["type"]] if entry.get("type") else [])
        results.append(
            {
                "name": entry.get("name"),
                "rating": entry.get("rating"),
                "review_count": entry.get("review_count"),
                "price_level": entry.get("price_level"),
                "address": entry.get("full_address"),
                "description": about.get("summary"),
                "types": types,
                "latitude": entry.get("latitude"),
                "longitude": entry.get("longitude"),
                "website": entry.get("website"),
            }
        )
    return results
