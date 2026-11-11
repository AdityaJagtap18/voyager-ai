"""
Multi-Agent Workflow with Integrated Dining
Orchestrates all agents with dining integrated into itinerary
"""
import time
from typing import TypedDict, List, Dict, Tuple, Optional
from langgraph.graph import StateGraph, END

from agents.research_agent import ResearchAgent
from agents.itinerary_agent import ItineraryAgent
from agents.dining_agent import DiningAgent
from agents.accommodation_agent import AccommodationAgent
from rag import get_context_for_destination
from utils.logger import logger


class TravelPlanState(TypedDict):
    """State shared across all agents"""
    destination: str
    days: int
    trip_type: str
    budget: str
    dietary_preferences: List[str]
    start_date: Optional[str]
    knowledge_context: str
    attractions: List[Dict]
    itinerary: Dict
    restaurants: List[Dict]
    accommodations: List[Dict]
    best_accommodation_location: Optional[Tuple[float, float]]
    current_step: str
    errors: List[str]
    trace: List[Dict]
    complete: bool


def _trace_entry(step: str, start: float, status: str, error: Optional[str] = None) -> Dict:
    """Build one observability trace entry (Phase 8) for a workflow step."""
    entry = {
        "step": step,
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
        "status": status,
    }
    if error:
        entry["error"] = error
    return entry


class MultiAgentWorkflow:
    """Orchestrates multiple agents with integrated dining in itinerary"""

    def __init__(self, model: Optional[str] = None):
        """model: a model id from app/llm_gateway.py's MODEL_REGISTRY (Phase 5);
        None uses the configured default (OPENAI_MODEL) for every agent."""
        logger.info(f"Initializing Multi-Agent Workflow with integrated dining (model={model or 'default'})")
        self.model = model
        self.research_agent = ResearchAgent(model=model)
        self.itinerary_agent = ItineraryAgent(model=model)
        self.dining_agent = DiningAgent(model=model)
        self.accommodation_agent = AccommodationAgent(model=model)
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
        start = time.monotonic()
        try:
            attractions = self.research_agent.find_attractions(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                knowledge_context=state.get("knowledge_context")
            )
            logger.info(f"Research complete: {len(attractions)} attractions found")
            trace_entry = _trace_entry("research", start, "success")
            return {"attractions": attractions, "current_step": "research_complete", "trace": state.get("trace", []) + [trace_entry]}
        except Exception as e:
            logger.error(f"Research Agent error: {str(e)}")
            trace_entry = _trace_entry("research", start, "error", str(e))
            return {"attractions": [], "errors": state.get("errors", []) + [str(e)], "trace": state.get("trace", []) + [trace_entry]}
    
    def _accommodation_node(self, state: TravelPlanState) -> Dict:
        """Step 2: Find accommodations near attractions"""
        logger.info("Step 2/4: Accommodation Agent - Finding hotels near attractions")
        start = time.monotonic()
        try:
            accommodations = self.accommodation_agent.find_accommodations(
                destination=state["destination"],
                trip_type=state["trip_type"],
                days=state["days"],
                budget=state.get("budget", "mid-range"),
                attractions=state["attractions"],
                start_date=state.get("start_date")
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
                "current_step": "accommodation_complete",
                "trace": state.get("trace", []) + [_trace_entry("accommodation", start, "success")]
            }
        except Exception as e:
            logger.error(f"Accommodation Agent error: {str(e)}")
            return {
                "accommodations": [],
                "best_accommodation_location": None,
                "errors": state.get("errors", []) + [str(e)],
                "trace": state.get("trace", []) + [_trace_entry("accommodation", start, "error", str(e))]
            }
    
    def _dining_node(self, state: TravelPlanState) -> Dict:
        """Step 3: Find restaurants near accommodation and attractions"""
        logger.info("Step 3/4: Dining Agent - Finding restaurants")
        start = time.monotonic()
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
            return {"restaurants": restaurants, "current_step": "dining_complete", "trace": state.get("trace", []) + [_trace_entry("dining", start, "success")]}
        except Exception as e:
            logger.error(f"Dining Agent error: {str(e)}")
            return {"restaurants": [], "errors": state.get("errors", []) + [str(e)], "trace": state.get("trace", []) + [_trace_entry("dining", start, "error", str(e))]}

    def _itinerary_node(self, state: TravelPlanState) -> Dict:
        """Step 4: Create itinerary with integrated meals"""
        logger.info("Step 4/4: Itinerary Agent - Creating schedule with integrated dining")
        start = time.monotonic()
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
            return {"itinerary": itinerary, "complete": True, "current_step": "complete", "trace": state.get("trace", []) + [_trace_entry("itinerary", start, "success")]}
        except Exception as e:
            logger.error(f"Itinerary Agent error: {str(e)}")
            return {"itinerary": {}, "errors": state.get("errors", []) + [str(e)], "trace": state.get("trace", []) + [_trace_entry("itinerary", start, "error", str(e))]}
    
    def plan_trip(self, destination: str, days: int, trip_type: str,
                  budget: str = "mid-range", dietary_preferences: List[str] = None,
                  start_date: Optional[str] = None) -> Dict:
        """Execute the complete multi-agent workflow"""
        logger.info("=" * 60)
        logger.info("Starting Multi-Agent Travel Planning with Integrated Dining")
        logger.info("=" * 60)

        try:
            knowledge_context = get_context_for_destination(destination)
        except Exception as e:
            logger.warning(f"RAG context lookup failed, continuing without it: {e}")
            knowledge_context = ""

        initial_state: TravelPlanState = {
            "destination": destination,
            "days": days,
            "trip_type": trip_type,
            "budget": budget,
            "dietary_preferences": dietary_preferences or [],
            "start_date": start_date,
            "knowledge_context": knowledge_context,
            "attractions": [],
            "itinerary": {},
            "restaurants": [],
            "accommodations": [],
            "best_accommodation_location": None,
            "current_step": "initialized",
            "errors": [],
            "trace": [],
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
                "errors": final_state["errors"],
                "trace": final_state["trace"]
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


def create_workflow(model: Optional[str] = None) -> MultiAgentWorkflow:
    """Factory function to create a workflow instance"""
    return MultiAgentWorkflow(model=model)