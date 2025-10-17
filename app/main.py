"""
Voyager - AI Travel Planner
Main entry point
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.research_agent import ResearchAgent
from utils.logger import logger
import json


def get_user_input():
    """Get trip details from user"""
    print("\n" + "="*60)
    print(" VOYAGER - AI Travel Planner")
    print("="*60 + "\n")
    
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
        "7": "nature"
    }
    
    while True:
        choice = input("\n   Select trip type (1-7): ").strip()
        if choice in trip_types:
            trip_type = trip_types[choice]
            break
        else:
            print("     Please enter a number between 1 and 7")
    
    return destination, days, trip_type


def main():
    """Main function to run the travel planner"""
    
    # Get user input
    destination, days, trip_type = get_user_input()
    
    # Show selected options
    print("\n" + "-"*60)
    print(" YOUR TRIP DETAILS:")
    print(f"   Destination: {destination}")
    print(f"   Duration: {days} days")
    print(f"   Trip Type: {trip_type}")
    print("-"*60 + "\n")
    
    # Initialize Research Agent
    logger.info("Initializing Research Agent...")
    research_agent = ResearchAgent()
    
    # Find attractions
    attractions = research_agent.find_attractions(
        destination=destination,
        trip_type=trip_type,
        days=days
    )
    
    # Display results
    print("\n" + "="*60)
    print("RECOMMENDED ATTRACTIONS")
    print("="*60 + "\n")
    
    for i, attraction in enumerate(attractions, 1):
        print(f"{i}.{attraction['name']}")
        print(f"   Category: {attraction['category']}")
        print(f"   Duration: {attraction['duration']}")
        print(f"   Best Time: {attraction['best_time']}")
        print(f"    {attraction['description']}")
        print()
    
    # Save to file
    output_file = f"data/itineraries/{destination.replace(' ', '_').replace(',', '')}_attractions.json"
    
    # Create directory if doesn't exist
    os.makedirs("data/itineraries", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "destination": destination,
            "days": days,
            "trip_type": trip_type,
            "attractions": attractions
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")
    print("\n" + "="*60)
    print("Trip research complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()