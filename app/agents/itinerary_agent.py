"""
Itinerary Agent
Organizes attractions into a day-by-day schedule
"""
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from typing import List, Dict
import json

from config import Config
from utils.logger import logger


class ItineraryAgent:
    """Agent that creates day-by-day itinerary schedules"""
    
    def __init__(self):
        """Initialize the agent with OpenAI"""
        self.llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.OPENAI_TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        logger.info("📅 Itinerary Agent initialized")
    
    def create_schedule(
        self,
        attractions: List[Dict],
        days: int,
        trip_type: str
    ) -> Dict:
        """
        Organize attractions into a day-by-day schedule
        
        Args:
            attractions: List of attractions from research agent
            days: Number of days for the trip
            trip_type: Type of trip to optimize for
            
        Returns:
            Dictionary with day-by-day schedule
        """
        logger.info(f"📅 Creating {days}-day itinerary")
        
        # Format attractions for the prompt
        attractions_text = json.dumps(attractions, indent=2)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a travel itinerary planner expert.
            Given a list of attractions, organize them into an optimal day-by-day schedule.
            
            Consider:
            - Geographical proximity (group nearby attractions)
            - Best times to visit (morning/afternoon/evening)
            - Activity duration and pacing (don't overcrowd days)
            - Mix of activity types (balance museums, outdoors, dining)
            - Energy levels (lighter activities in evening)
            - Travel time between locations
            
            Return ONLY valid JSON in this exact format:
            {{
                "itinerary": [
                    {{
                        "day": 1,
                        "theme": "Brief theme for the day",
                        "activities": [
                            {{
                                "time": "09:00",
                                "name": "Attraction Name",
                                "duration": "2 hours",
                                "category": "museum",
                                "description": "Brief description",
                                "notes": "Any special tips or timing notes"
                            }}
                        ],
                        "total_activities": 3
                    }}
                ],
                "travel_tips": ["Tip 1", "Tip 2"],
                "packing_suggestions": ["Item 1", "Item 2"]
            }}
            
            Important:
            - Distribute attractions evenly across {days} days
            - Start days between 8-10 AM
            - Leave buffer time between activities
            - Include travel time considerations
            - End days by 8-9 PM
            - Return ONLY the JSON, no other text
            """),
            ("user", """Create a {days}-day itinerary for a {trip_type} trip.
            
            Available Attractions:
            {attractions}
            
            Optimize for: {trip_type} experiences
            Days: {days}
            """)
        ])
        
        # Create the chain and invoke
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "attractions": attractions_text,
                "days": days,
                "trip_type": trip_type
            })
            
            # Parse the response
            schedule_text = response.content
            
            # Clean markdown if present
            if "```json" in schedule_text:
                schedule_text = schedule_text.split("```json")[1].split("```")[0]
            elif "```" in schedule_text:
                schedule_text = schedule_text.split("```")[1].split("```")[0]
            
            schedule_text = schedule_text.strip()
            schedule = json.loads(schedule_text)
            
            logger.info(f"✅ Created schedule with {len(schedule.get('itinerary', []))} days")
            return schedule
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            return self._create_error_schedule(days, attractions)
        
        except Exception as e:
            logger.error(f"❌ Error creating schedule: {e}")
            return self._create_error_schedule(days, attractions)
    
    def _create_error_schedule(self, days: int, attractions: List[Dict]) -> Dict:
        """Create a basic fallback schedule"""
        per_day = max(1, len(attractions) // days)
        
        itinerary = []
        for day in range(1, days + 1):
            start_idx = (day - 1) * per_day
            end_idx = start_idx + per_day
            day_attractions = attractions[start_idx:end_idx]
            
            activities = []
            start_time = 9  # 9 AM
            for attr in day_attractions:
                activities.append({
                    "time": f"{start_time:02d}:00",
                    "name": attr.get("name", "Unknown"),
                    "duration": attr.get("duration", "2 hours"),
                    "category": attr.get("category", "activity"),
                    "description": attr.get("description", ""),
                    "notes": f"Best time: {attr.get('best_time', 'anytime')}"
                })
                start_time += 3  # 3 hour intervals
            
            itinerary.append({
                "day": day,
                "theme": f"Day {day} Exploration",
                "activities": activities,
                "total_activities": len(activities)
            })
        
        return {
            "itinerary": itinerary,
            "travel_tips": ["Check opening hours before visiting"],
            "packing_suggestions": ["Comfortable walking shoes", "Water bottle"]
        }