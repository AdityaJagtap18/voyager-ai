"""
Accommodation Agent
Recommends hotels and places to stay
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict
import json

from config import Config
from utils.logger import logger


class AccommodationAgent:
    """Agent that recommends accommodations"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("🏨 Accommodation Agent initialized")
    
    def find_accommodations(
        self,
        destination: str,
        trip_type: str,
        days: int,
        budget: str = "medium"
    ) -> List[Dict]:
        """
        Find accommodation recommendations
        
        Args:
            destination: City/location
            trip_type: Type of trip
            days: Number of days
            budget: "budget", "medium", or "luxury"
            
        Returns:
            List of accommodation recommendations
        """
        logger.info(f"🏨 Finding accommodations in {destination}")
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a travel accommodation expert.
            Recommend diverse lodging options based on destination, trip style, and budget.
            
            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Hotel/Hostel/Airbnb Name",
                    "type": "hotel/hostel/apartment/resort/boutique",
                    "location": "Neighborhood",
                    "price_per_night": "$50-100",
                    "rating": "4.5/5",
                    "amenities": ["wifi", "breakfast", "pool", "gym"],
                    "best_for": "couples/families/solo/groups",
                    "vibe": "modern/historic/boutique/budget-friendly",
                    "proximity": "Walking distance to attractions/Downtown/etc",
                    "highlights": ["Rooftop bar", "City views", "Free breakfast"],
                    "booking_tip": "Book in advance/Look for deals/etc",
                    "description": "Why this place stands out"
                }}
            ]
            
            Guidelines:
            - Recommend 3-5 options across different budgets
            - Match accommodation style to trip type
            - Consider location and accessibility
            - Budget preference: {budget}
            - Trip type: {trip_type}
            - Include mix of established hotels and unique stays
            - Be specific to {destination}
            - Return ONLY the JSON array
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Duration: {days} days
            Budget: {budget}
            
            Find accommodations that match this trip profile.
            """)
        ])
        
        # Create the chain and invoke
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "destination": destination,
                "trip_type": trip_type,
                "days": days,
                "budget": budget
            })
            
            # Parse the response
            accommodations_text = response.content
            
            # Clean markdown if present
            if "```json" in accommodations_text:
                accommodations_text = accommodations_text.split("```json")[1].split("```")[0]
            elif "```" in accommodations_text:
                accommodations_text = accommodations_text.split("```")[1].split("```")[0]
            
            accommodations_text = accommodations_text.strip()
            accommodations = json.loads(accommodations_text)
            
            logger.info(f"✅ Found {len(accommodations)} accommodation options")
            return accommodations
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            return self._create_error_response()
        
        except Exception as e:
            logger.error(f"❌ Error finding accommodations: {e}")
            return self._create_error_response()
    
    def _create_error_response(self) -> List[Dict]:
        """Create fallback response"""
        return [{
            "name": "Error finding accommodations",
            "type": "hotel",
            "location": "N/A",
            "price_per_night": "Check locally",
            "rating": "N/A",
            "amenities": [],
            "best_for": "all travelers",
            "vibe": "N/A",
            "proximity": "N/A",
            "highlights": [],
            "booking_tip": "Check popular booking sites",
            "description": "Please check local accommodation options"
        }]