"""
Multi-Agent Workflow
Orchestrates all agents using LangGraph
"""
from typing import TypedDict, List, Dict
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
    current_step: str
    errors: List[str]
    complete: bool


class MultiAgentWorkflow:
    """Orchestrates multiple agents using LangGraph"""
    
    def __init__(self):
        logger.info("Initializing Multi-Agent Workflow")
        self.research_agent = ResearchAgent()
        self.itinerary_agent = ItineraryAgent()
        self.dining_agent = DiningAgent()
        self.accommodation_agent = AccommodationAgent()
        self.graph = self._build_graph()
        logger.info("Multi-Agent Workflow ready")
    
    def _build_graph(self) -> StateGraph:
        """Build sequential workflow to avoid concurrent state updates"""
        workflow = StateGraph(TravelPlanState)
        
        workflow.add_node("research", self._research_node)
        workflow.add_node("itinerary", self._itinerary_node)
        workflow.add_node("dining", self._dining_node)
        workflow.add_node("accommodation", self._accommodation_node)
        
        workflow.set_entry_point("research")
        workflow.add_edge("research", "itinerary")
        workflow.add_edge("itinerary", "dining")
        workflow.add_edge("dining", "accommodation")
        workflow.add_edge("accommodation", END)
        
        return workflow.compile()
    
    def _research_node(self, state: TravelPlanState) -> Dict:
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
    
    def _itinerary_node(self, state: TravelPlanState) -> Dict:
        logger.info("Step 2/4: Itinerary Agent - Creating schedule")
        try:
            itinerary = self.itinerary_agent.create_schedule(
                attractions=state["attractions"],
                days=state["days"],
                trip_type=state["trip_type"]
            )
            logger.info("Itinerary complete")
            return {"itinerary": itinerary, "current_step": "itinerary_complete"}
        except Exception as e:
            logger.error(f"Itinerary Agent error: {str(e)}")
            return {"itinerary": {}, "errors": state.get("errors", []) + [str(e)]}
    
    def _dining_node(self, state: TravelPlanState) -> Dict:
        logger.info("Step 3/4: Dining Agent - Finding restaurants")
        try:
            restaurants = self.dining_agent.find_restaurants(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                dietary_preferences=state.get("dietary_preferences", [])
            )
            logger.info(f"Dining complete: {len(restaurants)} restaurants found")
            return {"restaurants": restaurants, "current_step": "dining_complete"}
        except Exception as e:
            logger.error(f"Dining Agent error: {str(e)}")
            return {"restaurants": [], "errors": state.get("errors", []) + [str(e)]}
    
    def _accommodation_node(self, state: TravelPlanState) -> Dict:
        logger.info("Step 4/4: Accommodation Agent - Finding accommodations")
        try:
            accommodations = self.accommodation_agent.find_accommodations(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                budget=state.get("budget", "medium")
            )
            logger.info(f"Accommodation complete: {len(accommodations)} options found")
            return {"accommodations": accommodations, "complete": True, "current_step": "complete"}
        except Exception as e:
            logger.error(f"Accommodation Agent error: {str(e)}")
            return {"accommodations": [], "errors": state.get("errors", []) + [str(e)]}
    
    def plan_trip(self, destination: str, days: int, trip_type: str, 
                  budget: str = "medium", dietary_preferences: List[str] = None) -> Dict:
        """Execute the complete multi-agent workflow"""
        logger.info("=" * 60)
        logger.info("Starting Multi-Agent Travel Planning")
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