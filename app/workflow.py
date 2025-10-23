"""
Multi-Agent Workflow with Integrated Dining
Orchestrates all agents with dining integrated into itinerary
"""
from typing import TypedDict, List, Dict, Tuple, Optional
from langgraph.graph import StateGraph, END

from agents.research_agent import ResearchAgent
from agents.itinerary_agent import ItineraryAgent
from agents.dining_agent import DiningAgent
from agents.accommodation_agent import AccommodationAgent
from utils.logger import logger


class TravelPlanState(TypedDict):
    """State shared across all agents"""
    destination: str
    days: int
    trip_type: str
    budget: str
    dietary_preferences: List[str]
    attractions: List[Dict]
    itinerary: Dict
    restaurants: List[Dict]
    accommodations: List[Dict]
    best_accommodation_location: Optional[Tuple[float, float]]
    current_step: str
    errors: List[str]
    complete: bool


class MultiAgentWorkflow:
    """Orchestrates multiple agents with integrated dining in itinerary"""
    
    def __init__(self):
        logger.info("Initializing Multi-Agent Workflow with integrated dining")
        self.research_agent = ResearchAgent()
        self.itinerary_agent = ItineraryAgent()
        self.dining_agent = DiningAgent()
        self.accommodation_agent = AccommodationAgent()
        self.graph = self._build_graph()
        logger.info("Multi-Agent Workflow ready")
    
    def _build_graph(self) -> StateGraph:
        """Build workflow: Research -> Accommodation -> Dining -> Itinerary (integrates meals)"""
        workflow = StateGraph(TravelPlanState)
        
        workflow.add_node("research", self._research_node)
        workflow.add_node("accommodation", self._accommodation_node)
        workflow.add_node("dining", self._dining_node)
        workflow.add_node("itinerary", self._itinerary_node)
        
        # Flow: Dining comes before Itinerary so meals can be integrated
        workflow.set_entry_point("research")
        workflow.add_edge("research", "accommodation")
        workflow.add_edge("accommodation", "dining")
        workflow.add_edge("dining", "itinerary")
        workflow.add_edge("itinerary", END)
        
        return workflow.compile()
    
    def _research_node(self, state: TravelPlanState) -> Dict:
        """Step 1: Find attractions"""
        logger.info("Step 1/4: Research Agent - Finding attractions")
        try:
            attractions = self.research_agent.find_attractions(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"]
            )
            logger.info(f"Research complete: {len(attractions)} attractions found")
            return {"attractions": attractions, "current_step": "research_complete"}
        except Exception as e:
            logger.error(f"Research Agent error: {str(e)}")
            return {"attractions": [], "errors": state.get("errors", []) + [str(e)]}
    
    def _accommodation_node(self, state: TravelPlanState) -> Dict:
        """Step 2: Find accommodations near attractions"""
        logger.info("Step 2/4: Accommodation Agent - Finding hotels near attractions")
        try:
            accommodations = self.accommodation_agent.find_accommodations(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                budget=state.get("budget", "medium"),
                attractions=state["attractions"]
            )
            
            # Get best accommodation location
            best_accommodation_location = None
            if accommodations:
                best_accom = self.accommodation_agent.get_best_accommodation(accommodations)
                if best_accom and best_accom.get('coordinates'):
                    best_accommodation_location = (
                        best_accom['coordinates']['lat'],
                        best_accom['coordinates']['lng']
                    )
                    logger.info(f"Best accommodation: {best_accom['name']}")
            
            logger.info(f"Accommodation complete: {len(accommodations)} options found")
            return {
                "accommodations": accommodations,
                "best_accommodation_location": best_accommodation_location,
                "current_step": "accommodation_complete"
            }
        except Exception as e:
            logger.error(f"Accommodation Agent error: {str(e)}")
            return {
                "accommodations": [],
                "best_accommodation_location": None,
                "errors": state.get("errors", []) + [str(e)]
            }
    
    def _dining_node(self, state: TravelPlanState) -> Dict:
        """Step 3: Find restaurants near accommodation and attractions"""
        logger.info("Step 3/4: Dining Agent - Finding restaurants")
        try:
            restaurants = self.dining_agent.find_restaurants(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                dietary_preferences=state.get("dietary_preferences", []),
                accommodation_location=state.get("best_accommodation_location"),
                attractions=state["attractions"]
            )
            logger.info(f"Dining complete: {len(restaurants)} restaurants found")
            return {"restaurants": restaurants, "current_step": "dining_complete"}
        except Exception as e:
            logger.error(f"Dining Agent error: {str(e)}")
            return {"restaurants": [], "errors": state.get("errors", []) + [str(e)]}
    
    def _itinerary_node(self, state: TravelPlanState) -> Dict:
        """Step 4: Create itinerary with integrated meals"""
        logger.info("Step 4/4: Itinerary Agent - Creating schedule with integrated dining")
        try:
            itinerary = self.itinerary_agent.create_schedule(
                attractions=state["attractions"],
                days=state["days"],
                trip_type=state["trip_type"],
                destination=state["destination"],
                restaurants=state.get("restaurants", []),
                accommodation_location=state.get("best_accommodation_location")
            )
            logger.info("Itinerary complete with integrated meals")
            return {"itinerary": itinerary, "complete": True, "current_step": "complete"}
        except Exception as e:
            logger.error(f"Itinerary Agent error: {str(e)}")
            return {"itinerary": {}, "errors": state.get("errors", []) + [str(e)]}
    
    def plan_trip(self, destination: str, days: int, trip_type: str, 
                  budget: str = "medium", dietary_preferences: List[str] = None) -> Dict:
        """Execute the complete multi-agent workflow"""
        logger.info("=" * 60)
        logger.info("Starting Multi-Agent Travel Planning with Integrated Dining")
        logger.info("=" * 60)
        
        initial_state: TravelPlanState = {
            "destination": destination,
            "days": days,
            "trip_type": trip_type,
            "budget": budget,
            "dietary_preferences": dietary_preferences or [],
            "attractions": [],
            "itinerary": {},
            "restaurants": [],
            "accommodations": [],
            "best_accommodation_location": None,
            "current_step": "initialized",
            "errors": [],
            "complete": False
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("=" * 60)
            logger.info("Multi-Agent Planning Complete!")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "destination": destination,
                "days": days,
                "trip_type": trip_type,
                "budget": budget,
                "plan": {
                    "attractions": final_state["attractions"],
                    "itinerary": final_state["itinerary"],
                    "restaurants": final_state["restaurants"],
                    "accommodations": final_state["accommodations"]
                },
                "errors": final_state["errors"]
            }
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "destination": destination,
                "days": days,
                "trip_type": trip_type
            }


def create_workflow() -> MultiAgentWorkflow:
    """Factory function to create a workflow instance"""
    return MultiAgentWorkflow()