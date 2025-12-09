"""
Research Agent
Finds attractions and points of interest based on destination and trip type
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict
import json

from config import Config
from utils.logger import logger


class ResearchAgent:
    """Agent that researches attractions for a destination"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info(" Research Agent initialized")
    
    def find_attractions(
        self, 
        destination: str, 
        trip_type: str, 
        days: int
    ) -> List[Dict]:
        """
        Find attractions for the given destination
        
        Args:
            destination: City/location (e.g., "Paris, France")
            trip_type: Type of trip (historic, adventure, foodie, relaxation, cultural)
            days: Number of days for the trip
            
        Returns:
            List of attractions with details
        """
        logger.info(f" Researching attractions for {destination}")
        logger.info(f"   Trip type: {trip_type}")
        logger.info(f"   Duration: {days} days")
        
        # Calculate how many attractions we need (roughly 2-3 per day)
        num_attractions = days * 2 + 2
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a travel expert helping plan trips. 
            Generate a list of top attractions based on the destination and trip type.
            
            Return ONLY a valid JSON array with this exact format:
            [
                {{
                    "name": "Attraction Name",
                    "description": "Brief 1-2 sentence description",
                    "category": "museum/park/historic site/restaurant/temple/etc",
                    "duration": "1-2 hours",
                    "best_time": "morning/afternoon/evening"
                }}
            ]
            
            Important:
            - Generate exactly {num_attractions} attractions
            - Focus on {trip_type} themed attractions
            - Include variety in categories
            - Be specific to {destination}
            - Return ONLY the JSON array, no other text
            """),
            ("user", "Destination: {destination}\nTrip Type: {trip_type}\nDays: {days}")
        ])
        
        # Create the chain and invoke
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "destination": destination,
                "trip_type": trip_type,
                "days": days,
                "num_attractions": num_attractions
            })
            
            # Parse the response
            attractions_text = response.content
            
            # Try to parse JSON
            try:
                # Remove any markdown code blocks if present
                if "```json" in attractions_text:
                    attractions_text = attractions_text.split("```json")[1].split("```")[0]
                elif "```" in attractions_text:
                    attractions_text = attractions_text.split("```")[1].split("```")[0]
                
                attractions_text = attractions_text.strip()
                attractions = json.loads(attractions_text)
                
                logger.info(f" Found {len(attractions)} attractions")
                return attractions
                
            except json.JSONDecodeError as e:
                logger.warning(f"  JSON parsing failed, trying alternative method")
                
                # Fallback: try to extract list using ast
                import ast
                start = attractions_text.find('[')
                end = attractions_text.rfind(']') + 1
                if start != -1 and end > start:
                    attractions_str = attractions_text[start:end]
                    attractions = ast.literal_eval(attractions_str)
                    logger.info(f" Found {len(attractions)} attractions (fallback method)")
                    return attractions
                else:
                    logger.error(f" Could not parse response")
                    return self._create_error_response(attractions_text)
        
        except Exception as e:
            logger.error(f" Error calling OpenAI: {e}")
            return self._create_error_response(str(e))
    
    def _create_error_response(self, error_msg: str) -> List[Dict]:
        """Create a fallback response when something goes wrong"""
        return [{
            "name": "Error occurred",
            "description": f"Could not fetch attractions. Error: {error_msg[:100]}",
            "category": "error",
            "duration": "N/A",
            "best_time": "N/A"
        }]


