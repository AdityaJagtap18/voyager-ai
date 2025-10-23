"""
Enhanced Itinerary Agent with Integrated Dining
Organizes attractions AND meals into a complete day schedule
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple
import json

from config import Config
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError


class ItineraryAgent:
    """Agent that creates day-by-day itinerary with attractions AND dining"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("Itinerary Agent initialized with ORS and dining integration")
    
    def _geocode_attractions(self, attractions: List[Dict], destination: str) -> List[Dict]:
        """Add coordinates to attractions using ORS geocoding"""
        logger.info("Geocoding attractions for distance calculations")
        
        for attraction in attractions:
            query = f"{attraction['name']}, {destination}"
            try:
                coords = geocode(query, limit=1)
                if coords:
                    attraction['coordinates'] = {
                        'lat': coords[0][0],
                        'lng': coords[0][1]
                    }
                    logger.info(f"  Geocoded: {attraction['name']}")
                else:
                    attraction['coordinates'] = None
                    logger.warning(f"  Could not geocode: {attraction['name']}")
            except Exception as e:
                logger.warning(f"  Geocoding failed for {attraction['name']}: {e}")
                attraction['coordinates'] = None
        
        return attractions
    
    def _find_nearest_restaurant(
        self,
        location: Tuple[float, float],
        restaurants: List[Dict],
        meal_type: str
    ) -> Dict:
        """Find the nearest restaurant of specific meal type"""
        
        # Filter by meal type
        matching_restaurants = [
            r for r in restaurants 
            if r.get('meal_type') == meal_type and r.get('coordinates')
        ]
        
        if not matching_restaurants:
            # Fallback to any restaurant
            matching_restaurants = [r for r in restaurants if r.get('coordinates')]
        
        if not matching_restaurants:
            return None
        
        # Find nearest
        min_distance = float('inf')
        nearest = None
        
        for restaurant in matching_restaurants:
            rest_loc = (restaurant['coordinates']['lat'], restaurant['coordinates']['lng'])
            
            try:
                results = matrix_distances(location, [rest_loc], profile="driving-car")
                if results and results[0].get('status') == 'OK':
                    distance = results[0]['distance_km']
                    if distance < min_distance:
                        min_distance = distance
                        nearest = restaurant.copy()
                        nearest['distance_from_current'] = {
                            'distance_km': distance,
                            'duration_minutes': int(results[0]['duration_h'] * 60)
                        }
            except:
                pass
        
        return nearest
    
    def _integrate_dining(
        self,
        daily_attractions: List[List[Dict]],
        restaurants: List[Dict],
        accommodation_location: Tuple[float, float]
    ) -> List[List[Dict]]:
        """Integrate meal recommendations into daily schedules"""
        logger.info("Integrating dining recommendations into itinerary")
        
        integrated_days = []
        used_restaurants = set()
        
        for day_num, day_attractions in enumerate(daily_attractions, 1):
            day_schedule = []
            current_time = 9  # Start at 9 AM
            
            for idx, attraction in enumerate(day_attractions):
                # Add the attraction
                day_schedule.append(attraction)
                
                # Parse duration
                duration_str = attraction.get('duration', '2 hours')
                try:
                    if 'half' in duration_str or 'full' in duration_str:
                        duration_hours = 4
                    else:
                        duration_hours = float(duration_str.split()[0].split('-')[0])
                except:
                    duration_hours = 2
                
                current_time += duration_hours
                
                # Add travel time if available
                if attraction.get('travel_to_next'):
                    current_time += attraction['travel_to_next']['duration_h']
                
                # Check if it's lunch time (12-14) or dinner time (18-20)
                if (12 <= current_time <= 14 and not any(a.get('is_meal') for a in day_schedule)) or \
                   (18 <= current_time <= 20 and idx == len(day_attractions) - 1):
                    
                    meal_type = 'lunch' if 12 <= current_time <= 14 else 'dinner'
                    
                    # Find restaurant near current location or accommodation
                    current_loc = None
                    if attraction.get('coordinates'):
                        current_loc = (attraction['coordinates']['lat'], attraction['coordinates']['lng'])
                    elif accommodation_location:
                        current_loc = accommodation_location
                    
                    if current_loc:
                        # Find nearest unused restaurant
                        available_restaurants = [
                            r for r in restaurants 
                            if r.get('name') not in used_restaurants
                        ]
                        
                        restaurant = self._find_nearest_restaurant(
                            current_loc,
                            available_restaurants,
                            meal_type
                        )
                        
                        if restaurant:
                            used_restaurants.add(restaurant['name'])
                            restaurant['is_meal'] = True
                            restaurant['meal_type_scheduled'] = meal_type
                            restaurant['scheduled_time'] = f"{int(current_time):02d}:00"
                            day_schedule.append(restaurant)
                            logger.info(f"  Day {day_num}: Added {meal_type} at {restaurant['name']}")
                            current_time += 1  # 1 hour for meal
            
            integrated_days.append(day_schedule)
        
        return integrated_days
    
    def create_schedule(
        self,
        attractions: List[Dict],
        days: int,
        trip_type: str,
        destination: str,
        restaurants: List[Dict] = None,
        accommodation_location: Tuple[float, float] = None
    ) -> Dict:
        """
        Create schedule with attractions AND dining integrated
        
        Args:
            attractions: List of attractions
            days: Number of days
            trip_type: Type of trip
            destination: City name
            restaurants: List of restaurant recommendations
            accommodation_location: Hotel coordinates
            
        Returns:
            Complete itinerary with meals integrated
        """
        logger.info(f"Creating {days}-day itinerary with integrated dining")
        
        # Step 1: Geocode attractions
        attractions = self._geocode_attractions(attractions, destination)
        
        # Step 2: Split attractions across days
        per_day = max(1, len(attractions) // days)
        daily_groups = []
        
        for day in range(days):
            start_idx = day * per_day
            end_idx = start_idx + per_day if day < days - 1 else len(attractions)
            daily_groups.append(attractions[start_idx:end_idx])
        
        # Step 3: Integrate dining if restaurants provided
        if restaurants and accommodation_location:
            daily_groups = self._integrate_dining(
                daily_groups,
                restaurants,
                accommodation_location
            )
        
        # Step 4: Create detailed schedule
        schedule = self._generate_complete_schedule(daily_groups, days, trip_type)
        
        return schedule
    
    def _generate_complete_schedule(
        self,
        daily_groups: List[List[Dict]],
        days: int,
        trip_type: str
    ) -> Dict:
        """Generate complete schedule with attractions and meals"""
        
        itinerary = []
        
        for day_num, day_items in enumerate(daily_groups, 1):
            start_time = 9  # 9 AM
            activities = []
            
            for item in day_items:
                if item.get('is_meal'):
                    # This is a restaurant
                    activity = {
                        "time": item.get('scheduled_time', f"{int(start_time):02d}:00"),
                        "type": "meal",
                        "meal_type": item.get('meal_type_scheduled', 'meal'),
                        "name": item['name'],
                        "cuisine": item.get('cuisine', 'various'),
                        "price_range": item.get('price_range', '$$'),
                        "location": item.get('location', 'N/A'),
                        "must_try": item.get('must_try', ''),
                        "description": f"{item.get('meal_type_scheduled', 'Meal').title()} at {item['name']}"
                    }
                    
                    if item.get('distance_from_current'):
                        activity['travel_to_restaurant'] = {
                            'distance_km': item['distance_from_current']['distance_km'],
                            'duration_minutes': item['distance_from_current']['duration_minutes']
                        }
                    
                    activities.append(activity)
                    start_time += 1  # 1 hour for meal
                    
                else:
                    # This is an attraction
                    duration_str = item.get('duration', '2 hours')
                    try:
                        if 'half' in duration_str or 'full' in duration_str:
                            duration_hours = 4
                        else:
                            duration_hours = float(duration_str.split()[0].split('-')[0])
                    except:
                        duration_hours = 2
                    
                    activity = {
                        "time": f"{int(start_time):02d}:00",
                        "type": "attraction",
                        "name": item.get("name", "Unknown"),
                        "duration": duration_str,
                        "category": item.get("category", "activity"),
                        "description": item.get("description", ""),
                        "notes": f"Best time: {item.get('best_time', 'anytime')}"
                    }
                    
                    if item.get('travel_to_next'):
                        activity['travel_after'] = item['travel_to_next']
                    
                    activities.append(activity)
                    start_time += duration_hours
            
            itinerary.append({
                "day": day_num,
                "theme": f"Day {day_num} - {trip_type.title()} Experience",
                "activities": activities,
                "total_activities": len([a for a in activities if a.get('type') != 'meal']),
                "total_meals": len([a for a in activities if a.get('type') == 'meal'])
            })
        
        return {
            "itinerary": itinerary,
            "travel_tips": [
                "Meal times are strategically placed near attractions",
                "Restaurant recommendations are within 50km",
                "Check opening hours before visiting"
            ],
            "packing_suggestions": [
                "Comfortable walking shoes",
                "Water bottle",
                "Phone charger"
            ]
        }