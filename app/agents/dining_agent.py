"""
Dining Agent with ORS Integration
Recommends restaurants near attractions or accommodation
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple, Optional
import json

from config import Config
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError


class DiningAgent:
    """Agent that recommends restaurants with location-based filtering"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("Dining Agent initialized with ORS integration")
    
    def find_restaurants(
        self,
        destination: str,
        trip_type: str,
        days: int,
        dietary_preferences: List[str] = None,
        accommodation_location: Optional[Tuple[float, float]] = None,
        attractions: List[Dict] = None
    ) -> List[Dict]:
        """
        Find restaurant recommendations near accommodation or attractions
        
        Args:
            destination: City/location
            trip_type: Type of trip
            days: Number of days
            dietary_preferences: Optional dietary restrictions
            accommodation_location: (lat, lng) of where user is staying
            attractions: List of attractions with coordinates
            
        Returns:
            List of restaurant recommendations with distances
        """
        logger.info(f"Finding restaurants in {destination}")
        
        # Calculate restaurants needed
        num_restaurants = days * 2  # 2 main meals per day
        
        # Get initial restaurant recommendations from LLM
        restaurants = self._get_restaurant_recommendations(
            destination, trip_type, num_restaurants, dietary_preferences
        )
        
        # Geocode restaurants
        restaurants = self._geocode_restaurants(restaurants, destination)
        
        # Calculate distances from accommodation if provided
        if accommodation_location:
            restaurants = self._add_distances_from_accommodation(
                restaurants, accommodation_location
            )
        
        # If attractions provided, find restaurants near each attraction cluster
        if attractions:
            restaurants = self._match_restaurants_to_attractions(
                restaurants, attractions
            )
        
        # Sort by distance from accommodation (handle missing values)
        if accommodation_location:
            restaurants.sort(key=lambda x: x.get('distance_from_accommodation', {}).get('distance_km', float('inf')))
        
        return restaurants
    
    def _get_restaurant_recommendations(
        self,
        destination: str,
        trip_type: str,
        num_restaurants: int,
        dietary_preferences: List[str]
    ) -> List[Dict]:
        """Get restaurant recommendations from LLM"""
        
        dietary_text = ", ".join(dietary_preferences) if dietary_preferences else "no restrictions"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a local food expert and restaurant critic.
            Recommend diverse dining experiences with SPECIFIC ADDRESSES or neighborhoods.
            
            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Italian/French/Local/etc",
                    "price_range": "$/$$/$$$",
                    "meal_type": "breakfast/lunch/dinner",
                    "specialties": ["dish1", "dish2"],
                    "atmosphere": "casual/fine dining/street food/etc",
                    "location": "Specific address or well-known intersection",
                    "neighborhood": "District/area name",
                    "must_try": "Signature dish",
                    "avg_cost": "$15-25 per person",
                    "reservation": "required/recommended/walk-in",
                    "description": "Why visit this place"
                }}
            ]
            
            IMPORTANT: Include specific location details so we can geocode it.
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Number needed: {num_restaurants}
            Dietary: {dietary_preferences}
            
            Provide {num_restaurants} restaurants with specific locations.
            """)
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "destination": destination,
                "trip_type": trip_type,
                "num_restaurants": num_restaurants,
                "dietary_preferences": dietary_text
            })
            
            restaurants_text = response.content
            
            if "```json" in restaurants_text:
                restaurants_text = restaurants_text.split("```json")[1].split("```")[0]
            elif "```" in restaurants_text:
                restaurants_text = restaurants_text.split("```")[1].split("```")[0]
            
            restaurants_text = restaurants_text.strip()
            restaurants = json.loads(restaurants_text)
            
            logger.info(f"Got {len(restaurants)} restaurant recommendations")
            return restaurants
            
        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []
    
    def _geocode_restaurants(self, restaurants: List[Dict], destination: str) -> List[Dict]:
        """Add coordinates to restaurants"""
        logger.info("Geocoding restaurants")
        
        for restaurant in restaurants:
            # Try with full address first
            query = f"{restaurant['name']}, {restaurant.get('location', '')}, {destination}"
            
            try:
                coords = geocode(query, limit=1)
                if coords:
                    restaurant['coordinates'] = {
                        'lat': coords[0][0],
                        'lng': coords[0][1]
                    }
                    logger.info(f"  Geocoded: {restaurant['name']}")
                else:
                    # Try with just name and destination
                    query = f"{restaurant['name']}, {destination}"
                    coords = geocode(query, limit=1)
                    if coords:
                        restaurant['coordinates'] = {
                            'lat': coords[0][0],
                            'lng': coords[0][1]
                        }
                        logger.info(f"  Geocoded (fallback): {restaurant['name']}")
                    else:
                        restaurant['coordinates'] = None
                        logger.warning(f"  Could not geocode: {restaurant['name']}")
            except Exception as e:
                logger.warning(f"  Geocoding failed for {restaurant['name']}: {e}")
                restaurant['coordinates'] = None
        
        return restaurants
    
    def _add_distances_from_accommodation(
        self,
        restaurants: List[Dict],
        accommodation_location: Tuple[float, float]
    ) -> List[Dict]:
        """Calculate distances from accommodation to each restaurant and filter by 50km"""
        logger.info("Calculating distances from accommodation")
        
        # Prepare destinations (restaurants with coordinates)
        dest_points = []
        dest_indices = []
        
        for idx, restaurant in enumerate(restaurants):
            if restaurant.get('coordinates'):
                dest_points.append((
                    restaurant['coordinates']['lat'],
                    restaurant['coordinates']['lng']
                ))
                dest_indices.append(idx)
        
        if not dest_points:
            logger.warning("No restaurants have coordinates for distance calculation")
            return restaurants
        
        try:
            # Batch calculate distances
            results = matrix_distances(
                accommodation_location,
                dest_points,
                profile="driving-car"
            )
            
            # Add distances to restaurants and mark for filtering
            for i, result in enumerate(results):
                restaurant_idx = dest_indices[i]
                if result.get('status') == 'OK':
                    distance_km = result['distance_km']
                    restaurants[restaurant_idx]['distance_from_accommodation'] = {
                        'distance_km': distance_km,
                        'duration_h': result['duration_h'],
                        'duration_minutes': int(result['duration_h'] * 60)
                    }
                    
                    # Mark restaurants over 50km away
                    if distance_km > 50:
                        restaurants[restaurant_idx]['too_far'] = True
                        logger.info(f"  {restaurants[restaurant_idx]['name']}: {distance_km}km (TOO FAR - excluding)")
                    else:
                        restaurants[restaurant_idx]['too_far'] = False
                        logger.info(f"  {restaurants[restaurant_idx]['name']}: {distance_km}km from accommodation")
                else:
                    restaurants[restaurant_idx]['distance_from_accommodation'] = None
                    restaurants[restaurant_idx]['too_far'] = True
        
        except Exception as e:
            logger.error(f"Error calculating distances: {e}")
        
        # Filter out restaurants over 50km
        filtered_restaurants = [r for r in restaurants if not r.get('too_far', False)]
        logger.info(f"Filtered to {len(filtered_restaurants)} restaurants within 50km")
        
        return filtered_restaurants
    
    def _match_restaurants_to_attractions(
        self,
        restaurants: List[Dict],
        attractions: List[Dict]
    ) -> List[Dict]:
        """Find which attraction each restaurant is closest to - ONLY for restaurants within 50km"""
        logger.info("Matching restaurants to nearby attractions (limited to 5 main attractions)")
        
        # Limit to first 5 attractions to speed up processing
        top_attractions = [a for a in attractions if a.get('coordinates')][:5]
        
        if not top_attractions:
            logger.warning("No attractions have coordinates")
            return restaurants
        
        for restaurant in restaurants:
            # Skip if already marked as too far or no coordinates
            if restaurant.get('too_far') or not restaurant.get('coordinates'):
                continue
            
            rest_loc = (restaurant['coordinates']['lat'], restaurant['coordinates']['lng'])
            
            min_distance = float('inf')
            nearest_attraction = None
            
            for attraction in top_attractions:
                attr_loc = (attraction['coordinates']['lat'], attraction['coordinates']['lng'])
                
                try:
                    results = matrix_distances(rest_loc, [attr_loc], profile="foot-walking")
                    
                    if results and results[0].get('status') == 'OK':
                        distance = results[0]['distance_km']
                        
                        # Only match if within 50km
                        if distance < 50 and distance < min_distance:
                            min_distance = distance
                            nearest_attraction = {
                                'name': attraction['name'],
                                'distance_km': distance,
                                'duration_minutes': int(results[0]['duration_h'] * 60)
                            }
                except Exception as e:
                    logger.warning(f"  Error calculating distance: {e}")
                    continue
            
            if nearest_attraction:
                restaurant['nearest_attraction'] = nearest_attraction
                logger.info(f"  {restaurant['name']} is near {nearest_attraction['name']} ({nearest_attraction['distance_km']}km)")
        
        return restaurants
    
    def _create_error_response(self) -> List[Dict]:
        """Create fallback response"""
        return [{
            "name": "Error finding restaurants",
            "cuisine": "various",
            "price_range": "$$",
            "meal_type": "any",
            "specialties": [],
            "atmosphere": "N/A",
            "location": "N/A",
            "neighborhood": "N/A",
            "must_try": "Local recommendations",
            "avg_cost": "Check locally",
            "reservation": "recommended",
            "description": "Please check local dining guides"
        }]