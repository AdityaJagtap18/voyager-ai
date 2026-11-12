"""
Accommodation Agent with ORS Integration
Recommends hotels near main tourist attractions
"""
from datetime import date, timedelta
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple, Optional
import json

from llm_gateway import get_chat_model
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError
from services import hotels_api
from services.hotels_api import HotelsAPIError


class AccommodationAgent:
    """Agent that recommends accommodations near attractions"""

    def __init__(self, model: Optional[str] = None):
        """Initialize the agent with a chat model from the model gateway (Phase 5)"""
        self.llm = get_chat_model(model)
        logger.info("Accommodation Agent initialized with ORS integration")
    
    def find_accommodations(
        self,
        destination: str,
        trip_type: str,
        days: int,
        budget: str = "mid-range",
        attractions: List[Dict] = None,
        start_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Find accommodation recommendations near main attractions

        Args:
            destination: City/location
            trip_type: Type of trip
            days: Number of days
            budget: Budget level
            attractions: List of attractions with coordinates
            start_date: Optional "YYYY-MM-DD" check-in date (Phase 3 fusion).
                When set and the real hotels provider (RAPIDAPI_KEY) is
                configured, recommendations are grounded in real, live hotel
                listings instead of LLM-generated ones. Without it (or if the
                real lookup finds nothing), falls back to the original
                LLM-generated flow — never silently returns nothing just
                because a date wasn't given.

        Returns:
            List of accommodation recommendations with distances to attractions
        """
        logger.info(f"Finding accommodations in {destination}")

        accommodations = None
        if start_date:
            accommodations = self._get_real_hotels(destination, start_date, days)

        if accommodations is None:
            # Get accommodation recommendations from LLM
            accommodations = self._get_accommodation_recommendations(
                destination, trip_type, days, budget
            )
            # Geocode accommodations
            accommodations = self._geocode_accommodations(accommodations, destination)

        # If attractions provided, calculate average distance to attractions
        if attractions and any(a.get('coordinates') for a in attractions):
            accommodations = self._calculate_attraction_proximity(
                accommodations, attractions
            )
            
            # Sort by proximity to attractions. avg_distance_to_attractions is explicitly
            # set to None (not left missing) when a distance couldn't be calculated, so
            # `.get(key, default)` won't catch it - None must be mapped to +inf too, or
            # sorting two such entries raises "'<' not supported between NoneType and NoneType".
            accommodations.sort(
                key=lambda x: x.get('avg_distance_to_attractions') if x.get('avg_distance_to_attractions') is not None else float('inf')
            )
        
        return accommodations
    
    def _get_accommodation_recommendations(
        self,
        destination: str,
        trip_type: str,
        days: int,
        budget: str
    ) -> List[Dict]:
        """Get accommodation recommendations from LLM"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a travel accommodation expert with knowledge of Indian pricing and preferences.
            Recommend diverse lodging options with SPECIFIC ADDRESSES or landmarks.

            BUDGET GUIDE (Indian context):
            - Budget: ₹800-2000 per night (backpacker hostels, budget hotels)
            - Mid-range: ₹2000-5000 per night (comfortable hotels, good amenities)
            - Premium: ₹5000+ per night (luxury hotels, resorts, heritage properties)

            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Hotel/Hostel Name",
                    "type": "hotel/hostel/apartment/resort/boutique",
                    "location": "Specific address or landmark",
                    "neighborhood": "District/area name",
                    "price_per_night": "₹2000-3500",
                    "rating": "4.5/5",
                    "amenities": ["wifi", "breakfast", "pool"],
                    "best_for": "couples/families/solo/groups",
                    "vibe": "modern/historic/boutique/budget-friendly",
                    "proximity_to_center": "Walking distance/5 min drive/etc",
                    "highlights": ["Rooftop bar", "City views"],
                    "booking_tip": "Book in advance",
                    "description": "Why this place stands out"
                }}
            ]

            IMPORTANT:
            - Use INR (₹) for all pricing from Indian perspective
            - Include specific location details for accurate geocoding
            - Consider value for money that appeals to Indian travelers
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Duration: {days} days
            Budget: {budget}

            Recommend 5 accommodation options with specific addresses.
            Price all recommendations in INR (₹) appropriate for Indian travelers' budget expectations.
            """)
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "destination": destination,
                "trip_type": trip_type,
                "days": days,
                "budget": budget
            })
            
            accommodations_text = response.content
            
            if "```json" in accommodations_text:
                accommodations_text = accommodations_text.split("```json")[1].split("```")[0]
            elif "```" in accommodations_text:
                accommodations_text = accommodations_text.split("```")[1].split("```")[0]
            
            accommodations_text = accommodations_text.strip()
            accommodations = json.loads(accommodations_text)
            for accommodation in accommodations:
                accommodation["source"] = "llm"

            logger.info(f"Got {len(accommodations)} accommodation recommendations")
            return accommodations

        except Exception as e:
            logger.error(f"Error getting accommodations: {e}")
            return []

    def _get_real_hotels(self, destination: str, start_date: str, days: int) -> Optional[List[Dict]]:
        """
        Real, live hotel listings (Phase 3 fusion) via services/hotels_api.py
        (Booking.com), in the same dict shape _get_accommodation_recommendations()
        produces so downstream proximity scoring works unchanged either way.

        Returns None (not []) when real data isn't usable for any reason —
        provider unconfigured, destination unresolvable, no offers found, or a
        provider error — so the caller falls back to the LLM-generated flow
        instead of a trip silently ending up with zero accommodations.
        """
        if not hotels_api.is_configured():
            return None

        try:
            checkin = date.fromisoformat(start_date)
            checkout = checkin + timedelta(days=days)

            destinations = hotels_api.search_destination(destination)
            if not destinations:
                logger.warning(f"Real hotels: no destination match for '{destination}', falling back to LLM")
                return None
            dest = destinations[0]

            offers = hotels_api.search_hotels(
                dest["dest_id"], dest["search_type"], checkin.isoformat(), checkout.isoformat()
            )
            if not offers:
                logger.warning(f"Real hotels: no offers for '{destination}', falling back to LLM")
                return None

            accommodations = []
            for offer in offers[:5]:
                coordinates = None
                if offer.get("latitude") is not None and offer.get("longitude") is not None:
                    coordinates = {"lat": offer["latitude"], "lng": offer["longitude"]}

                rating = f"{offer['review_score']}/10" if offer.get("review_score") is not None else "N/A"
                stars = f"{offer['star_rating']}★" if offer.get("star_rating") else None

                accommodations.append({
                    "name": offer.get("name") or "Unnamed property",
                    "type": "hotel",
                    "location": destination,
                    "neighborhood": destination,
                    "price_per_night": offer.get("price_formatted") or (
                        f"{offer['price_raw']} {offer['currency']}" if offer.get("price_raw") is not None else "N/A"
                    ),
                    "rating": rating,
                    "amenities": [],
                    "best_for": "all travelers",
                    "vibe": offer.get("review_score_word") or "N/A",
                    "proximity_to_center": "N/A",
                    "highlights": [stars] if stars else [],
                    "booking_tip": "Live pricing and availability from Booking.com — prices can change, book promptly.",
                    "description": f"Real-time Booking.com listing, rated {offer.get('review_score_word') or 'N/A'} "
                                    f"({rating}).",
                    "coordinates": coordinates,
                    "source": "real",
                })

            logger.info(f"Got {len(accommodations)} real hotel listings for {destination}")
            return accommodations
        except (HotelsAPIError, ValueError, KeyError) as e:
            logger.warning(f"Real hotels lookup failed, falling back to LLM: {e}")
            return None

    def _geocode_accommodations(self, accommodations: List[Dict], destination: str) -> List[Dict]:
        """Add coordinates to accommodations"""
        logger.info("Geocoding accommodations")
        
        for accommodation in accommodations:
            # Try with full address
            query = f"{accommodation['name']}, {accommodation.get('location', '')}, {destination}"
            
            try:
                coords = geocode(query, limit=1)
                if coords:
                    accommodation['coordinates'] = {
                        'lat': coords[0][0],
                        'lng': coords[0][1]
                    }
                    logger.info(f"  Geocoded: {accommodation['name']}")
                else:
                    # Fallback to name + destination
                    query = f"{accommodation['name']}, {destination}"
                    coords = geocode(query, limit=1)
                    if coords:
                        accommodation['coordinates'] = {
                            'lat': coords[0][0],
                            'lng': coords[0][1]
                        }
                        logger.info(f"  Geocoded (fallback): {accommodation['name']}")
                    else:
                        accommodation['coordinates'] = None
                        logger.warning(f"  Could not geocode: {accommodation['name']}")
            except Exception as e:
                logger.warning(f"  Geocoding failed for {accommodation['name']}: {e}")
                accommodation['coordinates'] = None
        
        return accommodations
    
    def _calculate_attraction_proximity(
        self,
        accommodations: List[Dict],
        attractions: List[Dict]
    ) -> List[Dict]:
        """Calculate average distance from each accommodation to all attractions"""
        logger.info("Calculating proximity to attractions")
        
        # Get attraction coordinates
        attraction_coords = []
        for attraction in attractions:
            if attraction.get('coordinates'):
                attraction_coords.append((
                    attraction['coordinates']['lat'],
                    attraction['coordinates']['lng']
                ))
        
        if not attraction_coords:
            logger.warning("No attractions have coordinates")
            return accommodations
        
        # Calculate distances for each accommodation
        for accommodation in accommodations:
            if not accommodation.get('coordinates'):
                accommodation['avg_distance_to_attractions'] = None
                accommodation['distances_to_attractions'] = []
                continue
            
            accom_loc = (
                accommodation['coordinates']['lat'],
                accommodation['coordinates']['lng']
            )
            
            try:
                # Calculate distances to all attractions
                results = matrix_distances(
                    accom_loc,
                    attraction_coords,
                    profile="driving-car"
                )
                
                distances = []
                for i, result in enumerate(results):
                    if result.get('status') == 'OK':
                        distances.append({
                            'attraction': attractions[i]['name'],
                            'distance_km': result['distance_km'],
                            'duration_minutes': int(result['duration_h'] * 60)
                        })
                
                accommodation['distances_to_attractions'] = distances
                
                # Calculate average distance
                if distances:
                    avg_distance = sum(d['distance_km'] for d in distances) / len(distances)
                    accommodation['avg_distance_to_attractions'] = round(avg_distance, 2)
                    logger.info(f"  {accommodation['name']}: avg {avg_distance:.2f}km to attractions")
                else:
                    accommodation['avg_distance_to_attractions'] = None
                
            except Exception as e:
                logger.error(f"  Error calculating distances for {accommodation['name']}: {e}")
                accommodation['avg_distance_to_attractions'] = None
                accommodation['distances_to_attractions'] = []
        
        return accommodations
    
    def get_best_accommodation(self, accommodations: List[Dict]) -> Dict:
        """Get the accommodation with best proximity to attractions"""
        valid_accommodations = [
            a for a in accommodations 
            if a.get('avg_distance_to_attractions') is not None
        ]
        
        if not valid_accommodations:
            return accommodations[0] if accommodations else None
        
        return min(valid_accommodations, key=lambda x: x['avg_distance_to_attractions'])
    
    def _create_error_response(self) -> List[Dict]:
        """Create fallback response"""
        return [{
            "name": "Error finding accommodations",
            "type": "hotel",
            "location": "N/A",
            "neighborhood": "N/A",
            "price_per_night": "Check locally",
            "rating": "N/A",
            "amenities": [],
            "best_for": "all travelers",
            "vibe": "N/A",
            "proximity_to_center": "N/A",
            "highlights": [],
            "booking_tip": "Check popular booking sites",
            "description": "Please check local accommodation options"
        }]