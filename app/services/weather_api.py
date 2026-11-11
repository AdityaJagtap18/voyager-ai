# app/services/weather_api.py
"""
Real weather forecast (Phase 3), via OpenWeatherMap's free Geocoding + 5 Day /
3 Hour Forecast APIs. The free forecast endpoint only looks 5 days ahead —
documented here and surfaced as-is to the frontend, not papered over, since
promising a forecast for a trip further out would mean fabricating data.
"""
import os
from collections import defaultdict

import requests

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEOCODE_URL = "http://api.openweathermap.org/geo/1.0/direct"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


class WeatherAPIError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(OPENWEATHER_API_KEY)


def _require_key():
    if not OPENWEATHER_API_KEY:
        raise WeatherAPIError("OPENWEATHER_API_KEY not set")


def _get(url: str, params: dict) -> dict:
    try:
        r = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise WeatherAPIError(f"Request to {url} failed: {exc}")
    if r.status_code >= 400:
        raise WeatherAPIError(f"{url} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def geocode(destination: str) -> dict:
    """Resolve a free-text destination to {lat, lon, name, country}, or
    raise WeatherAPIError if nothing matches."""
    _require_key()
    results = _get(GEOCODE_URL, {"q": destination, "limit": 1, "appid": OPENWEATHER_API_KEY})
    if not results:
        raise WeatherAPIError(f"No location found for '{destination}'")
    first = results[0]
    return {"lat": first["lat"], "lon": first["lon"], "name": first["name"], "country": first.get("country")}


def get_forecast(destination: str, units: str = "metric") -> dict:
    """Returns {location: {name, country}, days: [{date, temp_min, temp_max,
    description, icon}]} covering up to 5 days (the free API's limit) —
    `days` may be shorter than a trip's full length."""
    _require_key()
    location = geocode(destination)
    data = _get(
        FORECAST_URL,
        {"lat": location["lat"], "lon": location["lon"], "appid": OPENWEATHER_API_KEY, "units": units},
    )

    by_date = defaultdict(list)
    for entry in data.get("list") or []:
        date = entry["dt_txt"].split(" ")[0]
        by_date[date].append(entry)

    days = []
    for date, entries in sorted(by_date.items()):
        temps = [e["main"]["temp"] for e in entries]
        # Prefer the entry closest to midday for the representative description/icon.
        midday = min(entries, key=lambda e: abs(int(e["dt_txt"].split(" ")[1].split(":")[0]) - 12))
        weather = (midday.get("weather") or [{}])[0]
        days.append(
            {
                "date": date,
                "temp_min": round(min(temps), 1),
                "temp_max": round(max(temps), 1),
                "description": weather.get("description"),
                "icon": weather.get("icon"),
            }
        )

    return {"location": {"name": location["name"], "country": location["country"]}, "days": days}
