"""
Dining Agent with ORS Integration
Recommends restaurants near attractions or accommodation
"""
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple, Optional
import json

from llm_gateway import get_chat_model
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError
from services import restaurants_api
from services.restaurants_api import RestaurantsAPIError


class DiningAgent:
    """Agent that recommends restaurants with location-based filtering"""

    def __init__(self, model: Optional[str] = None):
        """Initialize the agent with a chat model from the model gateway (Phase 5)"""
        self.llm = get_chat_model(model)
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

        # Real listings (dining fusion) only when there's no dietary
        # constraint for them to miss — the real provider has no dietary
        # filtering, while the LLM prompt below is explicitly dietary-aware,
        # so a constrained request always goes through the LLM path instead.
        restaurants = None
        if not dietary_preferences:
            restaurants = self._get_real_restaurants(destination, num_restaurants)

        if restaurants is None:
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
            ("system", """You are a local food expert and restaurant critic with knowledge of Indian dining preferences and pricing.
            Recommend diverse dining experiences with SPECIFIC ADDRESSES or neighborhoods.

            PRICING GUIDE (Indian perspective):
            - Budget (₹): ₹150-400 per person (street food, dhabas, casual eateries)
            - Mid-range (₹₹): ₹400-1000 per person (good restaurants, cafes)
            - Premium (₹₹₹): ₹1000+ per person (fine dining, upscale restaurants)

            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Italian/French/Local/etc",
                    "price_range": "₹/₹₹/₹₹₹",
                    "meal_type": "breakfast/lunch/dinner",
                    "specialties": ["dish1", "dish2"],
                    "atmosphere": "casual/fine dining/street food/etc",
                    "location": "Specific address or well-known intersection",
                    "neighborhood": "District/area name",
                    "must_try": "Signature dish",
                    "avg_cost": "₹300-500 per person",
                    "reservation": "required/recommended/walk-in",
                    "description": "Why visit this place"
                }}
            ]

            IMPORTANT:
            - Use INR (₹) for all pricing from Indian perspective
            - Include specific location details so we can geocode it
            - Consider value for money that appeals to Indian diners
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Number needed: {num_restaurants}
            Dietary: {dietary_preferences}

            Provide {num_restaurants} restaurants with specific locations.
            Price all recommendations in INR (₹) appropriate for Indian travelers' budget expectations.
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
            for restaurant in restaurants:
                restaurant["source"] = "llm"

            logger.info(f"Got {len(restaurants)} restaurant recommendations")
            return restaurants

        except Exception as e:
            logger.error(f"Error getting restaurants: {e}")
            return []

    def _get_real_restaurants(self, destination: str, num_restaurants: int) -> Optional[List[Dict]]:
        """
        Real, live restaurant listings (dining fusion) via
        services/restaurants_api.py (Local Business Data / Google Maps), in
        the same dict shape _get_restaurant_recommendations() produces so
        downstream geocoding/distance/matching logic works unchanged either
        way — these already come with coordinates, so they skip geocoding.

        Returns None (not []) when real data isn't usable for any reason —
        provider unconfigured, no listings found, or a provider error — so
        the caller falls back to the LLM-generated flow instead of a trip
        silently ending up with zero restaurants.
        """
        if not restaurants_api.is_configured():
            return None

        try:
            listings = restaurants_api.search_restaurants(destination, limit=num_restaurants)
            if not listings:
                logger.warning(f"Real restaurants: no listings for '{destination}', falling back to LLM")
                return None

            restaurants = []
            for listing in listings:
                coordinates = None
                if listing.get("latitude") is not None and listing.get("longitude") is not None:
                    coordinates = {"lat": listing["latitude"], "lng": listing["longitude"]}

                cuisine = ", ".join(listing.get("types") or []) or "Local"
                rating = f"{listing['rating']}/5" if listing.get("rating") is not None else "N/A"

                restaurants.append({
                    "name": listing.get("name") or "Unnamed restaurant",
                    "cuisine": cuisine,
                    "price_range": listing.get("price_level") or "N/A",
                    "meal_type": "any",
                    "specialties": [],
                    "atmosphere": cuisine,
                    "location": listing.get("address") or destination,
                    "neighborhood": destination,
                    "must_try": "See menu",
                    "avg_cost": listing.get("price_level") or "N/A",
                    "reservation": "recommended",
                    "description": listing.get("description")
                    or f"Real-time listing, rated {rating} ({listing.get('review_count') or 0} reviews).",
                    "coordinates": coordinates,
                    "source": "real",
                })

            logger.info(f"Got {len(restaurants)} real restaurant listings for {destination}")
            return restaurants
        except RestaurantsAPIError as e:
            logger.warning(f"Real restaurants lookup failed, falling back to LLM: {e}")
            return None

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