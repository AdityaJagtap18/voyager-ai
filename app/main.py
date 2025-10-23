"""
Voyager - AI Travel Planner (Multi-Agent Version)
Main entry point with LangGraph multi-agent workflow
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflow import create_workflow
from utils.logger import logger


def get_user_input():
    """Get trip details from user"""
    print("\n" + "=" * 60)
    print("🌍 VOYAGER - AI Travel Planner (Multi-Agent)")
    print("=" * 60 + "\n")

    # Get destination
    destination = input("📍 Enter destination (e.g., Paris, France): ").strip()

    # Get number of days
    while True:
        try:
            days = int(input("📅 Enter number of days (1-30): "))
            if 1 <= days <= 30:
                break
            else:
                print("    ⚠️ Please enter a number between 1 and 30")
        except ValueError:
            print("    ⚠️ Please enter a valid number")

    # Get trip type
    print("\n🎯 Trip Type Options:")
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
            print("    ⚠️ Please enter a number between 1 and 7")

    # Get budget
    print("\n💰 Budget Level:")
    print("   1. Budget-friendly")
    print("   2. Medium")
    print("   3. Luxury")

    budget_map = {"1": "budget", "2": "medium", "3": "luxury"}

    while True:
        choice = input("\n   Select budget (1-3, or press Enter for Medium): ").strip()
        if not choice:
            budget = "medium"
            break
        elif choice in budget_map:
            budget = budget_map[choice]
            break
        else:
            print("    ⚠️ Please enter 1, 2, or 3")

    # Get dietary preferences (optional)
    print("\n🍴 Dietary Preferences (optional):")
    print("   Enter any restrictions (comma-separated)")
    print("   Examples: vegetarian, vegan, gluten-free, halal, kosher")
    print("   Or press Enter to skip")

    dietary_input = input("\n   Dietary preferences: ").strip()
    dietary_preferences = [d.strip() for d in dietary_input.split(",")] if dietary_input else []

    return destination, days, trip_type, budget, dietary_preferences


def _normalize_activity(a: dict) -> dict:
    """
    Defensive normalization so display logic never KeyErrors.
    Accept both 'category' and 'type' keys, provide defaults for everything else.
    """
    return {
        "time": a.get("time") or "Time TBA",
        "name": a.get("name") or "Untitled Activity",
        "category": a.get("category", a.get("type", "Activity")),
        "duration": a.get("duration") or "Duration TBA",
        "description": a.get("description") or "",
        "notes": a.get("notes") or "",
    }


def _normalize_plan(plan: dict) -> dict:
    """
    Normalize plan structure enough for robust printing.
    """
    plan = plan or {}
    itinerary_block = plan.get("itinerary") or {}

    # Normalize each day's activities
    normalized_days = []
    for day_plan in itinerary_block.get("itinerary") or []:
        activities = day_plan.get("activities") or []
        activities = [_normalize_activity(a) for a in activities]
        total = day_plan.get("total_activities", len(activities))
        normalized_days.append(
            {
                "day": day_plan.get("day", "—"),
                "theme": day_plan.get("theme", "—"),
                "total_activities": total,
                "activities": activities,
            }
        )

    plan["itinerary"] = {
        "itinerary": normalized_days,
        "travel_tips": itinerary_block.get("travel_tips") or [],
        "packing_suggestions": itinerary_block.get("packing_suggestions") or [],
    }

    # Normalize other sections to lists
    plan["restaurants"] = plan.get("restaurants") or []
    plan["accommodations"] = plan.get("accommodations") or []
    return plan


def display_results(results: dict):
    """Display the complete travel plan (robust to missing fields)"""
    if not results.get("success"):
        print("\n❌ Planning failed!")
        print(f"Error: {results.get('error', 'Unknown error')}")
        return

    plan = _normalize_plan(results.get("plan") or {})

    # Header
    print("\n" + "=" * 60)
    print("📋 YOUR COMPLETE TRAVEL PLAN")
    print("=" * 60)
    print(f"📍 Destination: {results.get('destination', '—')}")
    print(f"📅 Duration: {results.get('days', '—')} days")
    print(f"🎯 Trip Type: {results.get('trip_type', '—')}")
    print(f"💰 Budget: {results.get('budget', '—')}")
    print("=" * 60 + "\n")

    # 1) Day-by-Day Itinerary
    itinerary = plan.get("itinerary") or {}
    days_list = itinerary.get("itinerary") or []
    if days_list:
        print("📅 DAY-BY-DAY ITINERARY")
        print("-" * 60)

        for day_plan in days_list:
            print(f"\n🗓️  Day {day_plan.get('day', '—')}: {day_plan.get('theme', '—')}")
            print(f"   Activities: {day_plan.get('total_activities', len(day_plan.get('activities') or []))}\n")

            for activity in (day_plan.get("activities") or []):
                print(f"   ⏰ {activity.get('time')} - {activity.get('name')}")
                print(f"      📍 {activity.get('category')} • ⏱️  {activity.get('duration')}")
                desc = activity.get("description")
                notes = activity.get("notes")
                if desc:
                    print(f"      {desc}")
                if notes:
                    print(f"      💡 {notes}")
                print()

        # Travel tips
        tips = itinerary.get("travel_tips") or []
        if tips:
            print("\n💡 TRAVEL TIPS:")
            for tip in tips:
                print(f"   • {tip}")

        # Packing suggestions
        packing = itinerary.get("packing_suggestions") or []
        if packing:
            print("\n🎒 PACKING SUGGESTIONS:")
            for item in packing:
                print(f"   • {item}")
        print()

    # 2) Restaurant Recommendations
    restaurants = plan.get("restaurants") or []
    if restaurants:
        print("\n" + "=" * 60)
        print("🍽️  RESTAURANT RECOMMENDATIONS")
        print("-" * 60)

        for i, r in enumerate(restaurants, 1):
            name = r.get("name", f"Restaurant {i}")
            cuisine = r.get("cuisine", "—")
            price = r.get("price_range", "—")
            meal = r.get("meal_type", "—")
            loc = r.get("location", "—")
            must = r.get("must_try", "—")
            cost = r.get("avg_cost", "—")
            res = r.get("reservation", "—")
            desc = r.get("description", "")
            print(f"\n{i}. {name}")
            print(f"   🍴 {cuisine} • {price} • {meal}")
            print(f"   📍 {loc}")
            print(f"   ⭐ Must Try: {must}")
            print(f"   💰 {cost}")
            print(f"   🎫 Reservation: {res}")
            if desc:
                print(f"   ✨ {desc}")
        print()

    # 3) Accommodation Options
    hotels = plan.get("accommodations") or []
    if hotels:
        print("\n" + "=" * 60)
        print("🏨 ACCOMMODATION OPTIONS")
        print("-" * 60)

        for i, h in enumerate(hotels, 1):
            name = h.get("name", f"Stay {i}")
            typ = h.get("type", "Hotel")
            vibe = h.get("vibe", "—")
            loc = h.get("location", "—")
            near = h.get("proximity_to_center")
            dist = h.get("avg_distance_to_attractions")
            price = h.get("price_per_night", "—")
            rating = h.get("rating", "—")
            best = h.get("best_for", "—")
            amenities = h.get("amenities") or []
            highlights = h.get("highlights") or []
            tip = h.get("booking_tip", "—")

            print(f"\n{i}. {name}")
            print(f"   🏷️  {typ} • {vibe}")
            print(f"   📍 {loc}")
            if near:
                print(f"   Location: {near}")
            if dist:
                print(f"   Avg distance to attractions: {dist}km")
            print(f"   💰 {price} per night")
            print(f"   ⭐ Rating: {rating}")
            print(f"   🎯 Best for: {best}")
            if amenities:
                print(f"   🛎️  Amenities: {', '.join(amenities[:4])}")
            if highlights:
                print(f"   ✨ Highlights: {', '.join(highlights)}")
            print(f"   💡 Tip: {tip}")
        print()

    # Warnings (if any)
    if results.get("errors"):
        print("\n⚠️  WARNINGS:")
        for error in results["errors"]:
            print(f"   • {error}")
        print()


def save_results(results: dict, destination: str):
    """Save results to JSON file"""
    output_dir = os.path.join("data", "itineraries")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{destination.replace(' ', '_').replace(',', '')}_{timestamp}.json"
    output_file = os.path.join(output_dir, filename)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full plan saved to: {output_file}")


def main():
    """Main function to run the multi-agent travel planner"""
    # Get user input
    destination, days, trip_type, budget, dietary_preferences = get_user_input()

    # Show selected options
    print("\n" + "-" * 60)
    print("📝 YOUR SELECTIONS:")
    print(f"   📍 Destination: {destination}")
    print(f"   📅 Duration: {days} days")
    print(f"   🎯 Trip Type: {trip_type}")
    print(f"   💰 Budget: {budget}")
    if dietary_preferences:
        print(f"   🍴 Dietary: {', '.join(dietary_preferences)}")
    print("-" * 60 + "\n")

    # Create and run workflow
    logger.info("Initializing Multi-Agent System...")
    workflow = create_workflow()

    # Plan the trip (with a small safety net)
    try:
        results = workflow.plan_trip(
            destination=destination,
            days=days,
            trip_type=trip_type,
            budget=budget,
            dietary_preferences=dietary_preferences,
        )
        if not isinstance(results, dict):
            raise TypeError("Workflow returned non-dict results")
    except Exception as e:
        logger.exception("Planning failed with an exception.")
        results = {"success": False, "error": f"{type(e).__name__}: {e}"}

    # Display results
    display_results(results)

    # Save to file
    if results.get("success"):
        save_results(results, destination)

    print("\n" + "=" * 60)
    print("✅ Multi-Agent Planning Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
