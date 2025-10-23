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

    budget_map = {
        "1": "budget",
        "2": "medium",
        "3": "luxury"
    }

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


def display_results(results: dict):
    """Display the complete travel plan"""
    
    if not results.get("success"):
        print("\n❌ Planning failed!")
        print(f"Error: {results.get('error', 'Unknown error')}")
        return
    
    plan = results["plan"]
    
    # Header
    print("\n" + "=" * 60)
    print("📋 YOUR COMPLETE TRAVEL PLAN")
    print("=" * 60)
    print(f"📍 Destination: {results['destination']}")
    print(f"📅 Duration: {results['days']} days")
    print(f"🎯 Trip Type: {results['trip_type']}")
    print(f"💰 Budget: {results['budget']}")
    print("=" * 60 + "\n")
    
    # 1. Day-by-Day Itinerary
    itinerary = plan.get("itinerary", {})
    if itinerary and itinerary.get("itinerary"):
        print("📅 DAY-BY-DAY ITINERARY")
        print("-" * 60)
        
        for day_plan in itinerary["itinerary"]:
            print(f"\n🗓️  Day {day_plan['day']}: {day_plan['theme']}")
            print(f"   Activities: {day_plan['total_activities']}")
            print()
            
            for activity in day_plan["activities"]:
                print(f"   ⏰ {activity['time']} - {activity['name']}")
                print(f"      📍 {activity['category']} • ⏱️  {activity['duration']}")
                print(f"      {activity['description']}")
                if activity.get('notes'):
                    print(f"      💡 {activity['notes']}")
                print()
        
        # Travel tips
        if itinerary.get("travel_tips"):
            print("\n💡 TRAVEL TIPS:")
            for tip in itinerary["travel_tips"]:
                print(f"   • {tip}")
        
        # Packing suggestions
        if itinerary.get("packing_suggestions"):
            print("\n🎒 PACKING SUGGESTIONS:")
            for item in itinerary["packing_suggestions"]:
                print(f"   • {item}")
        
        print()
    
    # 2. Restaurant Recommendations
    restaurants = plan.get("restaurants", [])
    if restaurants:
        print("\n" + "=" * 60)
        print("🍽️  RESTAURANT RECOMMENDATIONS")
        print("-" * 60)
        
        for i, restaurant in enumerate(restaurants, 1):
            print(f"\n{i}. {restaurant['name']}")
            print(f"   🍴 {restaurant['cuisine']} • {restaurant['price_range']} • {restaurant['meal_type']}")
            print(f"   📍 {restaurant['location']}")
            print(f"   ⭐ Must Try: {restaurant['must_try']}")
            print(f"   💰 {restaurant['avg_cost']}")
            print(f"   🎫 Reservation: {restaurant['reservation']}")
            print(f"   ✨ {restaurant['description']}")
        print()
    
    # 3. Accommodation Options
    accommodations = plan.get("accommodations", [])
    if accommodations:
        print("\n" + "=" * 60)
        print("🏨 ACCOMMODATION OPTIONS")
        print("-" * 60)
        
        for i, hotel in enumerate(accommodations, 1):
            print(f"\n{i}. {hotel['name']}")
            print(f"   🏷️  {hotel['type']} • {hotel['vibe']}")
            print(f"   📍 {hotel['location']} • {hotel['proximity']}")
            print(f"   💰 {hotel['price_per_night']} per night")
            print(f"   ⭐ Rating: {hotel['rating']}")
            print(f"   🎯 Best for: {hotel['best_for']}")
            
            if hotel.get('amenities'):
                print(f"   🛎️  Amenities: {', '.join(hotel['amenities'][:4])}")
            
            if hotel.get('highlights'):
                print(f"   ✨ Highlights: {', '.join(hotel['highlights'])}")
            
            print(f"   💡 Tip: {hotel['booking_tip']}")
        print()
    
    # Errors (if any)
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
    
    # Plan the trip
    results = workflow.plan_trip(
        destination=destination,
        days=days,
        trip_type=trip_type,
        budget=budget,
        dietary_preferences=dietary_preferences
    )
    
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