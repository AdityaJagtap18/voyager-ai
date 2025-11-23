"""
Accommodation Agent with ORS Integration
Recommends hotels near main tourist attractions
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict, Tuple
import json

from config import Config
from utils.logger import logger
from services.ors_api import geocode, matrix_distances, ORSError


class AccommodationAgent:
    """Agent that recommends accommodations near attractions"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("Accommodation Agent initialized with ORS integration")
    
    def find_accommodations(
        self,
        destination: str,
        trip_type: str,
        days: int,
        budget: str = "medium",
        attractions: List[Dict] = None
    ) -> List[Dict]:
        """
        Find accommodation recommendations near main attractions
        
        Args:
            destination: City/location
            trip_type: Type of trip
            days: Number of days
            budget: Budget level
            attractions: List of attractions with coordinates
            
        Returns:
            List of accommodation recommendations with distances to attractions
        """
        logger.info(f"Finding accommodations in {destination}")
        
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
            
            # Sort by proximity to attractions
            accommodations.sort(
                key=lambda x: x.get('avg_distance_to_attractions', float('inf'))
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
            ("system", """You are a travel accommodation expert.
            Recommend diverse lodging options with SPECIFIC ADDRESSES or landmarks.
            
            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Hotel/Hostel Name",
                    "type": "hotel/hostel/apartment/resort/boutique",
                    "location": "Specific address or landmark",
                    "neighborhood": "District/area name",
                    "price_per_night": "$50-100",
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
            
            IMPORTANT: Include specific location details for accurate geocoding.
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Duration: {days} days
            Budget: {budget}
            
            Recommend 5 accommodation options with specific addresses.
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
            
            logger.info(f"Got {len(accommodations)} accommodation recommendations")
            return accommodations
            
        except Exception as e:
            logger.error(f"Error getting accommodations: {e}")
            return []
    
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