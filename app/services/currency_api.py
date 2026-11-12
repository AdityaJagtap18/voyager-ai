"""
Currency conversion (Phase 11d) - real, live exchange rates via Frankfurter
(https://frankfurter.dev, ECB reference rates, no API key required). Never
estimates or hardcodes a rate: a failed/unreachable request returns None,
the same "real or nothing" discipline as every other provider in this
codebase (ors_api.py, flights_api.py, hotels_api.py, weather_api.py).

Rates are cached in-process per (base, target) pair for _CACHE_TTL_SECONDS
to avoid hitting the API on every request - exchange rates don't move
meaningfully within an hour, and this is a free, unauthenticated API that
deserves to not be hammered.
"""
import time
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.frankfurter.app"
_CACHE_TTL_SECONDS = 3600

# (base, target) -> (cached_at_epoch, rate, date)
_rate_cache: Dict[tuple, tuple] = {}


def is_configured() -> bool:
    """Always True: Frankfurter is free and keyless, unlike every other
    provider in this codebase - there is no credential to be missing."""
    return True


def get_rate(base: str, target: str) -> Optional[Dict[str, Any]]:
    """Returns {"rate": float, "date": str} for base->target, or None if the
    pair can't be resolved (unknown currency code, network/provider error)."""
    base = base.upper().strip()
    target = target.upper().strip()
    if base == target:
        return {"rate": 1.0, "date": None}

    cached = _rate_cache.get((base, target))
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return {"rate": cached[1], "date": cached[2]}

    try:
        resp = requests.get(f"{BASE_URL}/latest", params={"from": base, "to": target}, timeout=10)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        rate = (data.get("rates") or {}).get(target)
        if rate is None:
            return None
        _rate_cache[(base, target)] = (time.time(), rate, data.get("date"))
        return {"rate": rate, "date": data.get("date")}
    except requests.RequestException:
        return None


def convert(amount: float, base: str, target: str) -> Optional[Dict[str, Any]]:
    """Converts a real amount using a real rate. Returns None (never a
    fabricated conversion) when the rate can't be fetched."""
    rate_info = get_rate(base, target)
    if rate_info is None:
        return None
    return {
        "amount": amount,
        "from": base.upper().strip(),
        "to": target.upper().strip(),
        "rate": rate_info["rate"],
        "converted": round(amount * rate_info["rate"], 2),
        "date": rate_info["date"],
        "source": "real",
    }


def list_rates(base: str) -> Optional[Dict[str, Any]]:
    """All live rates for one base currency, for a converter UI's dropdown/table."""
    base = base.upper().strip()
    try:
        resp = requests.get(f"{BASE_URL}/latest", params={"from": base}, timeout=10)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        return {"base": base, "date": data.get("date"), "rates": data.get("rates") or {}, "source": "real"}
    except requests.RequestException:
        return None
