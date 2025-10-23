"""
Dining Agent
Recommends restaurants and dining experiences
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict
import json

from config import Config
from utils.logger import logger


class DiningAgent:
    """Agent that recommends restaurants and dining experiences"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("🍽️ Dining Agent initialized")
    
    def find_restaurants(
        self,
        destination: str,
        trip_type: str,
        days: int,
        dietary_preferences: List[str] = None
    ) -> List[Dict]:
        """
        Find restaurant recommendations
        
        Args:
            destination: City/location
            trip_type: Type of trip (affects restaurant style)
            days: Number of days (determines number of recommendations)
            dietary_preferences: Optional list like ["vegetarian", "halal", "gluten-free"]
            
        Returns:
            List of restaurant recommendations
        """
        logger.info(f"🍽️ Finding restaurants in {destination}")
        
        # Calculate restaurants needed (breakfast, lunch, dinner for each day)
        num_restaurants = days * 2  # 2 main meals per day
        
        dietary_text = ", ".join(dietary_preferences) if dietary_preferences else "no restrictions"
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a local food expert and restaurant critic.
            Recommend diverse dining experiences based on the destination and trip style.
            
            Return ONLY valid JSON array with this format:
            [
                {{
                    "name": "Restaurant Name",
                    "cuisine": "Italian/French/Local/etc",
                    "price_range": "$/$$/$$$",
                    "meal_type": "breakfast/lunch/dinner",
                    "specialties": ["dish1", "dish2"],
                    "atmosphere": "casual/fine dining/street food/etc",
                    "location": "Neighborhood or area",
                    "must_try": "Signature dish",
                    "avg_cost": "$15-25 per person",
                    "reservation": "required/recommended/walk-in",
                    "description": "Why visit this place"
                }}
            ]
            
            Guidelines:
            - Generate exactly {num_restaurants} restaurants
            - Mix of price ranges and meal types
            - Include local favorites AND hidden gems
            - Consider trip type: {trip_type}
            - Respect dietary preferences: {dietary_preferences}
            - Balance fine dining, casual, and street food
            - Be specific to {destination}
            - Return ONLY the JSON array
            """),
            ("user", """Destination: {destination}
            Trip Type: {trip_type}
            Days: {days}
            Dietary Preferences: {dietary_preferences}
            
            Find diverse, authentic restaurants that match this trip style.
            """)
        ])
        
        # Create the chain and invoke
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "destination": destination,
                "trip_type": trip_type,
                "days": days,
                "num_restaurants": num_restaurants,
                "dietary_preferences": dietary_text
            })
            
            # Parse the response
            restaurants_text = response.content
            
            # Clean markdown if present
            if "```json" in restaurants_text:
                restaurants_text = restaurants_text.split("```json")[1].split("```")[0]
            elif "```" in restaurants_text:
                restaurants_text = restaurants_text.split("```")[1].split("```")[0]
            
            restaurants_text = restaurants_text.strip()
            restaurants = json.loads(restaurants_text)
            
            logger.info(f"✅ Found {len(restaurants)} restaurant recommendations")
            return restaurants
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            return self._create_error_response()
        
        except Exception as e:
            logger.error(f"❌ Error finding restaurants: {e}")
            return self._create_error_response()
    
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
            "must_try": "Local recommendations",
            "avg_cost": "Check locally",
            "reservation": "recommended",
            "description": "Please check local dining guides"
        }]