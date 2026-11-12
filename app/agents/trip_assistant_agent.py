"""
Trip Assistant Agent (Phase 11c) - AI-powered conversational interaction
over real trip data.

Answers a free-text question about one trip by grounding the LLM's answer
in a snapshot of that trip's actual, already-computed data (budget
allocation, flight/transport recommendations, itinerary) - the model is
instructed to use only the numbers it's given, never to invent a price,
time, or availability of its own. This mirrors the "deterministic
calculation, LLM only to explain" split used throughout Phase 11:
budget_allocator.py and flight_recommendations.py compute every number;
this agent only talks about them.

Scope: single-turn Q&A over the trip's current state, not a persisted
multi-turn conversation - see docs/VOYAGER_IMPLEMENTATION_AUDIT.md for why
multi-turn history was left out of this slice.
"""
import json
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate

from llm_gateway import get_chat_model
from utils.logger import logger

SYSTEM_PROMPT = """You are Voyager's trip-planning assistant. You answer questions about ONE \
specific trip, using ONLY the data given to you below as TRIP_DATA.

Rules:
- Never invent a price, time, distance, or availability that is not present in TRIP_DATA.
- When you reference a number (a price, a distance, a duration, a score), it must come straight \
from TRIP_DATA - do not round, estimate, or make up a plausible-sounding figure.
- If TRIP_DATA doesn't contain what's needed to answer, say so plainly instead of guessing.
- Be concise and specific - a traveler is reading this on their phone.

TRIP_DATA (JSON):
{trip_data}
"""


class TripAssistantAgent:
    """Answers one question about a trip, grounded in that trip's real data."""

    def __init__(self, model: Optional[str] = None):
        self.llm = get_chat_model(model)

    def answer(self, question: str, trip_data: Dict[str, Any]) -> str:
        logger.info(" Trip Assistant: answering a question grounded in real trip data")
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"trip_data": json.dumps(trip_data, default=str), "question": question})
        return result.content if hasattr(result, "content") else str(result)
