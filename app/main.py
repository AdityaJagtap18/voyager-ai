"""
Voyager - AI Travel Planner
Main entry point
"""
import sys
import os
import json
import requests
import math  # <-- ADDED

# Add current directory (app) to Python path so local packages import cleanly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.research_agent import ResearchAgent
from utils.logger import logger
from services.ors_api import (
    geocode,
    route_distance_duration,
    matrix_distances,
    ORSError,
)


def get_user_input():
    """Get trip details from user"""
    print("\n" + "=" * 60)
    print(" VOYAGER - AI Travel Planner")
    print("=" * 60 + "\n")

    # Get destination
    destination = input(" Enter destination (e.g., Paris, France): ").strip()

    # Get number of days
    while True:
        try:
            days = int(input(" Enter number of days (1-30): "))
            if 1 <= days <= 30:
                break
            else:
                print("     Please enter a number between 1 and 30")
        except ValueError:
            print("     Please enter a valid number")

    # Get trip type
    print("\n Trip Type Options:")
    print("   1. Historic")
    print("   2. Adventure")
    print("   3. Relaxation")
    print("   4. Foodie")
    print("   5. Cultural")
    print("   6. Romantic")
    print("   7. Nature")

    trip_types = {
        "1": "historic",
        "2": "adventure",
        "3": "relaxation",
        "4": "foodie",
        "5": "cultural",
        "6": "romantic",
        "7": "nature",
    }

    while True:
        choice = input("\n   Select trip type (1-7): ").strip()
        if choice in trip_types:
            trip_type = trip_types[choice]
            break
        else:
            print("     Please enter a number between 1 and 7")

    return destination, days, trip_type


def geocode_fallback_nominatim(q: str, limit: int = 1):
    """
    Free fallback geocoder using OpenStreetMap Nominatim.
    Keeps your CLI resilient if ORS geocoding rate-limits or is ambiguous.
    """
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": str(limit)},
            headers={"User-Agent": "voyager-ai"},
            timeout=30,
        )
        resp.raise_for_status()
        js = resp.json()
        return [(float(it["lat"]), float(it["lon"])) for it in js][:limit]
    except Exception:
        return []


# ===================== ADDED HELPERS (for day-wise console output) =====================

def _dist_value_km(a):
    t = a.get("travel") or {}
    d = t.get("distance_km")
    try:
        return float(d)
    except Exception:
        return float("inf")

def split_into_days_evenly(attractions, days):
    """
    Sort by nearest-first (using travel.distance_km if present),
    then split evenly across the given number of days.
    """
    if not attractions:
        return [[] for _ in range(days)]
    ordered = sorted(attractions, key=_dist_value_km)
    per_day = max(1, math.ceil(len(ordered) / max(1, days)))
    groups = []
    for i in range(days):
        start = i * per_day
        chunk = ordered[start:start + per_day]
        if chunk:
            groups.append(chunk)
    return groups

def _fmt_km(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return None

def _fmt_hours(h):
    try:
        h = float(h)
        return f"{h:.2f} h" if h >= 1 else f"{round(h*60)} min"
    except Exception:
        return None

# ======================================================================================


def main():
    """Main function to run the travel planner"""

    # Get user input
    destination, days, trip_type = get_user_input()

    # Show selected options
    print("\n" + "-" * 60)
    print(" YOUR TRIP DETAILS:")
    print(f"   Destination: {destination}")
    print(f"   Duration: {days} days")
    print(f"   Trip Type: {trip_type}")
    print("-" * 60 + "\n")

    # Initialize Research Agent
    logger.info("Initializing Research Agent...")
    research_agent = ResearchAgent()

    # Find attractions
    attractions = research_agent.find_attractions(
        destination=destination,
        trip_type=trip_type,
        days=days,
    )

    # === Enrich with travel distance/duration (batch Matrix call) ===
    # 1) Geocode origin (destination city or "center")
    try:
        start_candidates = geocode(destination, limit=1)
    except Exception:
        start_candidates = geocode_fallback_nominatim(destination, limit=1)

    if not start_candidates:
        print("Could not geocode destination for routing. Skipping travel times.")
    else:
        start_latlng = start_candidates[0]

        # 2) Geocode all attractions first (with fallback)
        dest_points = []
        for a in attractions:
            query = f"{a['name']}, {destination}"
            try:
                pts = geocode(query, limit=1)
            except Exception:
                pts = []
            if not pts:
                pts = geocode_fallback_nominatim(query, limit=1)
            dest_points.append(pts[0] if pts else None)

        # 3) Build a compact list for matrix (only geocoded ones)
        idx_map = [i for i, p in enumerate(dest_points) if p is not None]
        matrix_input = [dest_points[i] for i in idx_map]

        # 4) Call ORS Matrix once; if it fails, fall back to per-item directions
        results = []
        if matrix_input:
            try:
                results = matrix_distances(
                    start_latlng, matrix_input, profile="driving-car"
                )
            except ORSError as e:
                # Fall back one-by-one (gentle pacing)
                results = []
                import time
                prev_point = start_latlng

                for p in matrix_input:
                    try:
                        d_km, h = route_distance_duration(prev_point, p, profile="driving-car")

                        results.append(
                            {
                                "distance_km": d_km,
                                "duration_h": h,
                                "status": "OK",
                                "error": None,
                            }
                        )
                        prev_point = p

                    except Exception as ee:
                        results.append(
                            {
                                "distance_km": None,
                                "duration_h": None,
                                "status": "ERR",
                                "error": str(ee),
                            }
                        )
                    time.sleep(0.2)

        # 5) Attach results back to attractions
        for a in attractions:
            a["travel"] = a.get("travel") or {}

        j = 0
        for i in range(len(attractions)):
            if dest_points[i] is None:
                attractions[i]["travel"] = {
                    "distance_km": None,
                    "duration_h": None,
                    "note": "geocode_failed",
                }
            else:
                if j < len(results):
                    r = results[j]
                    if r.get("status") == "OK":
                        attractions[i]["travel"] = {
                            "distance_km": r["distance_km"],
                            "duration_h": r["duration_h"],
                            "mode": "driving-car",
                        }
                    else:
                        attractions[i]["travel"] = {
                            "distance_km": None,
                            "duration_h": None,
                            "error": r.get("error") or "matrix_error",
                        }
                    j += 1
                else:
                    attractions[i]["travel"] = {
                        "distance_km": None,
                        "duration_h": None,
                        "error": "no_matrix_result",
                    }

    # === Display results (grouped by day) — ADDED DAY-WISE CONSOLE OUTPUT ===
    groups = split_into_days_evenly(attractions, days)

    print("\n" + "=" * 60)
    print("RECOMMENDED ITINERARY")
    print("=" * 60 + "\n")

    for day_idx, day_items in enumerate(groups, start=1):
        print(f"Day {day_idx}")
        print("-" * 60)

        for i, attraction in enumerate(day_items, 1):
            print(f"{i}. {attraction['name']}")
            print(f"   Category: {attraction['category']}")
            print(f"   Duration: {attraction['duration']}")
            print(f"   Best Time: {attraction['best_time']}")

            tr = attraction.get("travel") or {}
            d = tr.get("distance_km")
            t = tr.get("duration_h")
            mode = tr.get("mode", "")
            if d is not None and t is not None:
                d_str = _fmt_km(d)
                t_str = _fmt_hours(t)
                print(f"   Travel: {d_str} km • {t_str}" + (f" • {mode}" if mode else ""))
            elif tr.get("note") == "geocode_failed":
                print("   Travel: distance unavailable (geocode failed)")
            elif tr.get("error"):
                print(f"   Travel: distance unavailable ({tr['error']})")

            print(f"   {attraction['description']}\n")

        print()  # blank line between days

    # === Save to file ===
    output_dir = os.path.join("data", "itineraries")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir, f"{destination.replace(' ', '_').replace(',', '')}_attractions.json"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "destination": destination,
                "days": days,
                "trip_type": trip_type,
                "attractions": attractions,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Results saved to: {output_file}")
    print("\n" + "=" * 60)
    print("Trip research complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
