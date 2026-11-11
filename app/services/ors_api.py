# app/services/ors_api.py
import os
import time
import requests

ORS_API_KEY = os.getenv("ORS_API_KEY")

BASE_GEOCODE    = "https://api.openrouteservice.org/geocode/search"
BASE_DIRECTIONS = "https://api.openrouteservice.org/v2/directions"
BASE_MATRIX     = "https://api.openrouteservice.org/v2/matrix"

class ORSError(RuntimeError):
    pass

def _headers():
    if not ORS_API_KEY:
        raise ORSError("ORS_API_KEY not set. In PowerShell: $env:ORS_API_KEY='YOUR_ORS_KEY'")
    return {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

# app/services/ors_api.py

def geocode(text: str, limit: int = 1, focus: tuple | None = None, radius_km: float | None = None):
    """
    Return list[(lat, lng)] using ORS Geocoding.
    Supports biasing toward a city center with Pelias focus params.
    focus: (lat, lng)
    radius_km: optional boundary circle around focus
    """
    if not ORS_API_KEY:
        raise ORSError("ORS_API_KEY not set")

    params = {"text": text, "size": limit}
    if focus:
        lat, lng = focus
        params["focus.point.lat"] = lat
        params["focus.point.lon"] = lng
        if radius_km:
            params["boundary.circle.lat"] = lat
            params["boundary.circle.lon"] = lng
            params["boundary.circle.radius"] = radius_km  # km

    r = requests.get(
        BASE_GEOCODE,
        headers={"Authorization": ORS_API_KEY},
        params=params,
        timeout=30
    )
    if r.status_code == 429:
        time.sleep(1.0)
        r = requests.get(
            BASE_GEOCODE,
            headers={"Authorization": ORS_API_KEY},
            params=params,
            timeout=30
        )
    if r.status_code >= 400:
        try:
            j = r.json()
            msg = j.get("error", {}).get("message") or j.get("message") or r.text
        except Exception:
            msg = r.text
        raise ORSError(f"Geocode failed {r.status_code}: {msg}")

    j = r.json()
    feats = j.get("features") or []
    coords = []
    for feat in feats:
        # ORS returns [lng, lat]
        lng, lat = feat["geometry"]["coordinates"]
        coords.append((lat, lng))
    return coords

def route_distance_duration(origin_latlng, dest_latlng, profile="driving-car"):
    """(km, hours) via ORS Directions."""
    url = f"{BASE_DIRECTIONS}/{profile}"
    body = {"coordinates": [[origin_latlng[1], origin_latlng[0]],
                            [dest_latlng[1],   dest_latlng[0]]]}
    r = requests.post(url, json=body, headers=_headers(), timeout=60)
    if r.status_code == 429:
        time.sleep(1.0)
        r = requests.post(url, json=body, headers=_headers(), timeout=60)
    if r.status_code >= 400:
        try:
            j = r.json()
            msg = j.get("error", {}).get("message") or j.get("message") or r.text
        except Exception:
            msg = r.text
        raise ORSError(f"Directions failed {r.status_code}: {msg}")

    j = r.json()
    feats = j.get("features")
    if not feats:
        raise ORSError(f"Directions response missing 'features': {j}")
    summary = feats[0]["properties"]["summary"]
    return round(summary["distance"] / 1000.0, 2), round(summary["duration"] / 3600.0, 2)

def matrix_distances(origin_latlng, dest_latlng_list, profile="driving-car"):
    """
    Batch distance/duration from one origin to many destinations.
    Returns list aligned to dest_latlng_list:
      [{"distance_km": float|None, "duration_h": float|None, "status": "OK"|"ERR", "error": str|None}, ...]
    """
    url = f"{BASE_MATRIX}/{profile}"
    locations = [[origin_latlng[1], origin_latlng[0]]] + [[d[1], d[0]] for d in dest_latlng_list]
    body = {
        "locations": locations,
        "sources": [0],
        "destinations": list(range(1, len(locations))),
        "metrics": ["distance", "duration"]
    }
    r = requests.post(url, json=body, headers=_headers(), timeout=60)
    if r.status_code == 429:
        time.sleep(1.0)
        r = requests.post(url, json=body, headers=_headers(), timeout=60)
    if r.status_code >= 400:
        try:
            j = r.json()
            msg = j.get("error", {}).get("message") or j.get("message") or r.text
        except Exception:
            msg = r.text
        raise ORSError(f"Matrix failed {r.status_code}: {msg}")

    j = r.json()
    distances = j.get("distances", [[]])[0] if j.get("distances") else []
    durations = j.get("durations", [[]])[0] if j.get("durations") else []
    out = []
    for i in range(len(dest_latlng_list)):
        try:
            d_m = distances[i]
            s   = durations[i]
            if d_m is None or s is None:
                out.append({"distance_km": None, "duration_h": None, "status": "ERR", "error": "no_path"})
            else:
                out.append({"distance_km": round(d_m/1000.0, 2),
                            "duration_h": round(s/3600.0, 2),
                            "status": "OK", "error": None})
        except Exception as e:
            out.append({"distance_km": None, "duration_h": None, "status": "ERR", "error": str(e)})
    return out
