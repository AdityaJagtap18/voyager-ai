"""
CrewAI orchestration adapter (Phase 6).

Demonstrates that the travel-planning pipeline isn't tied to LangGraph: this
drives the exact same four agent objects (ResearchAgent, AccommodationAgent,
DiningAgent, ItineraryAgent — unchanged, same prompts, same real ORS
geocoding in the itinerary step) through CrewAI's own Agent/Task/Crew/
Process.sequential primitives instead of app/workflow.py's StateGraph.

Each CrewAI Agent gets exactly one zero-argument tool that calls straight
into the matching agent method and stores the result on a shared
_TripContext — closures, not LLM-supplied arguments, since the trip's
destination/days/etc. are already known and there's nothing for the model to
get wrong by filling them in itself. Each tool is declared
`result_as_answer=True`, which makes CrewAI use the tool's return value as
the task's final output verbatim instead of letting the agent's LLM
paraphrase it — this matters most for the itinerary step, whose schedule
comes from real geocoding/distance math, not the LLM; paraphrasing it would
silently replace real data with a hallucinated summary.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

from agents.accommodation_agent import AccommodationAgent
from agents.dining_agent import DiningAgent
from agents.itinerary_agent import ItineraryAgent
from agents.research_agent import ResearchAgent
from rag import get_context_for_destination
from utils.logger import logger


@dataclass
class _TripContext:
    destination: str
    days: int
    trip_type: str
    budget: str
    dietary_preferences: List[str]
    start_date: Optional[str] = None
    attractions: List[Dict] = field(default_factory=list)
    accommodations: List[Dict] = field(default_factory=list)
    best_accommodation_location: Optional[Tuple[float, float]] = None
    restaurants: List[Dict] = field(default_factory=list)
    itinerary: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    knowledge_context: str = ""
    trace: List[Dict] = field(default_factory=list)


def _trace_entry(step: str, start: float, status: str, error: Optional[str] = None) -> Dict:
    """Build one observability trace entry (Phase 8) for a CrewAI tool step."""
    entry = {
        "step": step,
        "duration_ms": round((time.monotonic() - start) * 1000, 1),
        "status": status,
    }
    if error:
        entry["error"] = error
    return entry


class CrewAIOrchestrator:
    """Same `plan_trip(...) -> dict` contract as app.workflow.MultiAgentWorkflow."""

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.research_agent = ResearchAgent(model=model)
        self.accommodation_agent = AccommodationAgent(model=model)
        self.dining_agent = DiningAgent(model=model)
        self.itinerary_agent = ItineraryAgent(model=model)

    def plan_trip(
        self,
        destination: str,
        days: int,
        trip_type: str,
        budget: str = "mid-range",
        dietary_preferences: Optional[List[str]] = None,
        start_date: Optional[str] = None,
    ) -> Dict:
        ctx = _TripContext(
            destination=destination,
            days=days,
            trip_type=trip_type,
            budget=budget,
            dietary_preferences=dietary_preferences or [],
            start_date=start_date,
        )
        try:
            ctx.knowledge_context = get_context_for_destination(destination)
        except Exception as exc:
            logger.warning(f"RAG context lookup failed, continuing without it: {exc}")

        @tool("research_attractions", result_as_answer=True)
        def research_attractions() -> str:
            """Find attractions for the trip's destination and trip type."""
            start = time.monotonic()
            try:
                ctx.attractions = self.research_agent.find_attractions(
                    destination=ctx.destination,
                    trip_type=ctx.trip_type,
                    days=ctx.days,
                    knowledge_context=ctx.knowledge_context,
                )
                ctx.trace.append(_trace_entry("research", start, "success"))
            except Exception as exc:
                ctx.errors.append(str(exc))
                ctx.trace.append(_trace_entry("research", start, "error", str(exc)))
            return f"Found {len(ctx.attractions)} attractions"

        @tool("find_accommodations", result_as_answer=True)
        def find_accommodations() -> str:
            """Find accommodations near the attractions already researched."""
            start = time.monotonic()
            try:
                ctx.accommodations = self.accommodation_agent.find_accommodations(
                    destination=ctx.destination,
                    trip_type=ctx.trip_type,
                    days=ctx.days,
                    budget=ctx.budget,
                    attractions=ctx.attractions,
                    start_date=ctx.start_date,
                )
                if ctx.accommodations:
                    best = self.accommodation_agent.get_best_accommodation(ctx.accommodations)
                    if best and best.get("coordinates"):
                        ctx.best_accommodation_location = (
                            best["coordinates"]["lat"],
                            best["coordinates"]["lng"],
                        )
                ctx.trace.append(_trace_entry("accommodation", start, "success"))
            except Exception as exc:
                ctx.errors.append(str(exc))
                ctx.trace.append(_trace_entry("accommodation", start, "error", str(exc)))
            return f"Found {len(ctx.accommodations)} accommodations"

        @tool("find_restaurants", result_as_answer=True)
        def find_restaurants() -> str:
            """Find restaurants near the accommodation, honoring dietary preferences."""
            start = time.monotonic()
            try:
                ctx.restaurants = self.dining_agent.find_restaurants(
                    destination=ctx.destination,
                    trip_type=ctx.trip_type,
                    days=ctx.days,
                    dietary_preferences=ctx.dietary_preferences,
                    accommodation_location=ctx.best_accommodation_location,
                    attractions=ctx.attractions,
                )
                ctx.trace.append(_trace_entry("dining", start, "success"))
            except Exception as exc:
                ctx.errors.append(str(exc))
                ctx.trace.append(_trace_entry("dining", start, "error", str(exc)))
            return f"Found {len(ctx.restaurants)} restaurants"

        @tool("build_itinerary", result_as_answer=True)
        def build_itinerary() -> str:
            """Build the day-by-day schedule with meals integrated (real geocoding + route optimization)."""
            start = time.monotonic()
            try:
                ctx.itinerary = self.itinerary_agent.create_schedule(
                    attractions=ctx.attractions,
                    days=ctx.days,
                    trip_type=ctx.trip_type,
                    destination=ctx.destination,
                    restaurants=ctx.restaurants,
                    accommodation_location=ctx.best_accommodation_location,
                )
                ctx.trace.append(_trace_entry("itinerary", start, "success"))
            except Exception as exc:
                ctx.errors.append(str(exc))
                ctx.trace.append(_trace_entry("itinerary", start, "error", str(exc)))
            return "Itinerary built"

        llm = self.model or "gpt-3.5-turbo"

        research_crew_agent = Agent(
            role="Travel Researcher",
            goal=f"Find the best attractions in {destination} for a {trip_type} trip",
            backstory="An expert local guide who knows every attraction worth visiting.",
            tools=[research_attractions],
            llm=llm,
            allow_delegation=False,
            verbose=False,
        )
        accommodation_crew_agent = Agent(
            role="Accommodation Scout",
            goal="Find well-located lodging near the trip's attractions",
            backstory="A hotel concierge who always finds a place close to the action.",
            tools=[find_accommodations],
            llm=llm,
            allow_delegation=False,
            verbose=False,
        )
        dining_crew_agent = Agent(
            role="Dining Scout",
            goal="Find restaurants that fit the trip's dietary preferences",
            backstory="A food writer with a mental map of every good meal in town.",
            tools=[find_restaurants],
            llm=llm,
            allow_delegation=False,
            verbose=False,
        )
        itinerary_crew_agent = Agent(
            role="Itinerary Planner",
            goal="Schedule the attractions and meals into a realistic day-by-day plan",
            backstory="A logistics planner who always accounts for travel time between stops.",
            tools=[build_itinerary],
            llm=llm,
            allow_delegation=False,
            verbose=False,
        )

        research_task = Task(
            description=f"Call the research_attractions tool to find attractions in {destination}.",
            expected_output="A short confirmation of how many attractions were found.",
            agent=research_crew_agent,
        )
        accommodation_task = Task(
            description="Call the find_accommodations tool to find lodging near the attractions just researched.",
            expected_output="A short confirmation of how many accommodations were found.",
            agent=accommodation_crew_agent,
            context=[research_task],
        )
        dining_task = Task(
            description="Call the find_restaurants tool to find restaurants near the accommodation.",
            expected_output="A short confirmation of how many restaurants were found.",
            agent=dining_crew_agent,
            context=[research_task, accommodation_task],
        )
        itinerary_task = Task(
            description="Call the build_itinerary tool to build the final day-by-day schedule.",
            expected_output="A short confirmation that the itinerary was built.",
            agent=itinerary_crew_agent,
            context=[research_task, accommodation_task, dining_task],
        )

        crew = Crew(
            agents=[research_crew_agent, accommodation_crew_agent, dining_crew_agent, itinerary_crew_agent],
            tasks=[research_task, accommodation_task, dining_task, itinerary_task],
            process=Process.sequential,
            verbose=False,
        )

        try:
            crew.kickoff()
        except Exception as exc:
            logger.error(f"CrewAI orchestration failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "destination": destination,
                "days": days,
                "trip_type": trip_type,
            }

        return {
            "success": True,
            "destination": destination,
            "days": days,
            "trip_type": trip_type,
            "budget": budget,
            "plan": {
                "attractions": ctx.attractions,
                "itinerary": ctx.itinerary,
                "restaurants": ctx.restaurants,
                "accommodations": ctx.accommodations,
            },
            "errors": ctx.errors,
            "trace": ctx.trace,
        }
