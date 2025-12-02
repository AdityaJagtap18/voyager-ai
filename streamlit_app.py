"""
Voyager AI - Streamlit Frontend
Basic web interface for the AI Travel Planner
"""

import streamlit as st
import sys
import os
import json
from datetime import datetime

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.workflow import create_workflow
from app.utils.logger import logger

# Page configuration
st.set_page_config(
    page_title="Voyager AI - Travel Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .activity-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .restaurant-card {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .accommodation-card {
        background-color: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'planning' not in st.session_state:
        st.session_state.planning = False

def display_itinerary(itinerary_data):
    """Display the day-by-day itinerary"""
    st.header("📅 Day-by-Day Itinerary")

    days_list = itinerary_data.get("itinerary", [])
    if not days_list:
        st.warning("No itinerary data available")
        return

    for day_plan in days_list:
        day_num = day_plan.get("day", "—")
        theme = day_plan.get("theme", "—")

        with st.expander(f"🗓️ Day {day_num}: {theme}", expanded=(day_num == 1)):
            activities = day_plan.get("activities", [])
            st.write(f"**Total Activities:** {len(activities)}")

            for activity in activities:
                time = activity.get("time", "Time TBA")
                name = activity.get("name", "Untitled Activity")
                category = activity.get("category", activity.get("type", "Activity"))
                duration = activity.get("duration", "Duration TBA")
                description = activity.get("description", "")
                notes = activity.get("notes", "")

                st.markdown(f"""
                <div class="activity-card">
                    <strong>⏰ {time} - {name}</strong><br>
                    📍 {category} • ⏱️ {duration}<br>
                    {f'<em>{description}</em><br>' if description else ''}
                    {f'💡 {notes}' if notes else ''}
                </div>
                """, unsafe_allow_html=True)

    # Travel tips
    tips = itinerary_data.get("travel_tips", [])
    if tips:
        st.subheader("💡 Travel Tips")
        for tip in tips:
            st.info(tip)

    # Packing suggestions
    packing = itinerary_data.get("packing_suggestions", [])
    if packing:
        st.subheader("🎒 Packing Suggestions")
        cols = st.columns(2)
        for idx, item in enumerate(packing):
            cols[idx % 2].write(f"• {item}")

def display_restaurants(restaurants):
    """Display restaurant recommendations"""
    st.header("🍽️ Restaurant Recommendations")

    if not restaurants:
        st.warning("No restaurant recommendations available")
        return

    for idx, restaurant in enumerate(restaurants, 1):
        name = restaurant.get("name", f"Restaurant {idx}")
        cuisine = restaurant.get("cuisine", "—")
        price_range = restaurant.get("price_range", "—")
        meal_type = restaurant.get("meal_type", "—")
        location = restaurant.get("location", "—")
        must_try = restaurant.get("must_try", "—")
        avg_cost = restaurant.get("avg_cost", "—")
        reservation = restaurant.get("reservation", "—")
        description = restaurant.get("description", "")

        st.markdown(f"""
        <div class="restaurant-card">
            <h4>{idx}. {name}</h4>
            🍴 {cuisine} • {price_range} • {meal_type}<br>
            📍 {location}<br>
            ⭐ <strong>Must Try:</strong> {must_try}<br>
            💰 {avg_cost}<br>
            🎫 <strong>Reservation:</strong> {reservation}<br>
            {f'<em>{description}</em>' if description else ''}
        </div>
        """, unsafe_allow_html=True)

def display_accommodations(accommodations):
    """Display accommodation options"""
    st.header("🏨 Accommodation Options")

    if not accommodations:
        st.warning("No accommodation options available")
        return

    for idx, hotel in enumerate(accommodations, 1):
        name = hotel.get("name", f"Stay {idx}")
        hotel_type = hotel.get("type", "Hotel")
        vibe = hotel.get("vibe", "—")
        location = hotel.get("location", "—")
        proximity = hotel.get("proximity_to_center", "")
        avg_distance = hotel.get("avg_distance_to_attractions", "")
        price = hotel.get("price_per_night", "—")
        rating = hotel.get("rating", "—")
        best_for = hotel.get("best_for", "—")
        amenities = hotel.get("amenities", [])
        highlights = hotel.get("highlights", [])
        tip = hotel.get("booking_tip", "—")

        st.markdown(f"""
        <div class="accommodation-card">
            <h4>{idx}. {name}</h4>
            🏷️ {hotel_type} • {vibe}<br>
            📍 {location}<br>
            {f'Location: {proximity}<br>' if proximity else ''}
            {f'Avg distance to attractions: {avg_distance}km<br>' if avg_distance else ''}
            💰 {price} per night<br>
            ⭐ <strong>Rating:</strong> {rating}<br>
            🎯 <strong>Best for:</strong> {best_for}<br>
            {f"🛎️ <strong>Amenities:</strong> {', '.join(amenities[:4])}<br>" if amenities else ''}
            {f"✨ <strong>Highlights:</strong> {', '.join(highlights)}<br>" if highlights else ''}
            💡 <strong>Tip:</strong> {tip}
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main Streamlit app"""
    initialize_session_state()

    # Header
    st.markdown('<div class="main-header">🌍 VOYAGER AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Travel Planner with Multi-Agent System</div>', unsafe_allow_html=True)

    # Sidebar for input
    with st.sidebar:
        st.header("📝 Trip Details")

        # Destination
        destination = st.text_input(
            "📍 Destination",
            placeholder="e.g., Paris, France",
            help="Enter the city and country you want to visit"
        )

        # Number of days
        days = st.slider(
            "📅 Number of Days",
            min_value=1,
            max_value=30,
            value=3,
            help="Select trip duration (1-30 days)"
        )

        # Trip type
        trip_type = st.selectbox(
            "🎯 Trip Type",
            options=["historic", "adventure", "relaxation", "foodie", "cultural", "romantic", "nature"],
            help="Select the type of trip you want"
        )

        # Budget
        budget_display = st.selectbox(
            "💰 Budget Level",
            options=[
                "Budget (₹800-2000/night, ₹150-400/meal)",
                "Mid-range (₹2000-5000/night, ₹400-1000/meal)",
                "Premium (₹5000+/night, ₹1000+/meal)"
            ],
            index=1,
            help="Select your budget level (Indian pricing)"
        )

        # Map display to internal value
        budget_map = {
            "Budget (₹800-2000/night, ₹150-400/meal)": "budget",
            "Mid-range (₹2000-5000/night, ₹400-1000/meal)": "mid-range",
            "Premium (₹5000+/night, ₹1000+/meal)": "premium"
        }
        budget = budget_map[budget_display]

        # Dietary preferences
        st.subheader("🍴 Dietary Preferences (Optional)")
        dietary_input = st.text_input(
            "Dietary Restrictions",
            placeholder="e.g., vegetarian, gluten-free",
            help="Enter dietary preferences separated by commas"
        )
        dietary_preferences = [d.strip() for d in dietary_input.split(",")] if dietary_input else []

        # Generate button
        generate_button = st.button("🚀 Generate Itinerary", type="primary", use_container_width=True)

    # Main content area
    if generate_button:
        if not destination:
            st.error("Please enter a destination!")
            return

        st.session_state.planning = True

        # Show user selections
        st.info(f"""
        **Your Selections:**
        - 📍 Destination: {destination}
        - 📅 Duration: {days} days
        - 🎯 Trip Type: {trip_type}
        - 💰 Budget: {budget}
        {f"- 🍴 Dietary: {', '.join(dietary_preferences)}" if dietary_preferences else ""}
        """)

        # Progress indicator
        with st.spinner("🤖 AI agents are working on your travel plan..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # Create workflow
                status_text.text("Initializing multi-agent system...")
                progress_bar.progress(10)
                workflow = create_workflow()

                # Run planning
                status_text.text("Step 1/4: Research Agent - Finding attractions...")
                progress_bar.progress(25)

                results = workflow.plan_trip(
                    destination=destination,
                    days=days,
                    trip_type=trip_type,
                    budget=budget,
                    dietary_preferences=dietary_preferences
                )

                progress_bar.progress(100)
                status_text.text("Planning complete!")

                st.session_state.results = results
                st.session_state.planning = False

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                logger.exception("Planning failed")
                st.session_state.planning = False
                return

    # Display results
    if st.session_state.results:
        results = st.session_state.results

        if not results.get("success"):
            st.error(f"Planning failed: {results.get('error', 'Unknown error')}")
            return

        # Success message
        st.success("✅ Your travel plan is ready!")

        # Get plan data
        plan = results.get("plan", {})
        itinerary = plan.get("itinerary", {})
        restaurants = plan.get("restaurants", [])
        accommodations = plan.get("accommodations", [])

        # Create tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["📅 Itinerary", "🍽️ Restaurants", "🏨 Accommodations", "📥 Download"])

        with tab1:
            display_itinerary(itinerary)

        with tab2:
            display_restaurants(restaurants)

        with tab3:
            display_accommodations(accommodations)

        with tab4:
            st.header("📥 Download Your Plan")
            st.write("Download your complete travel plan as a JSON file for future reference.")

            # Create JSON for download
            json_str = json.dumps(results, indent=2, ensure_ascii=False)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{destination.replace(' ', '_').replace(',', '')}_{timestamp}.json"

            st.download_button(
                label="💾 Download JSON",
                data=json_str,
                file_name=filename,
                mime="application/json",
                use_container_width=True
            )

            # Display any warnings
            if results.get("errors"):
                st.warning("⚠️ Some issues occurred during planning:")
                for error in results["errors"]:
                    st.write(f"• {error}")

if __name__ == "__main__":
    main()
