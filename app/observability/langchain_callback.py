"""
A LangChain callback handler that turns every LLM call into an OTel span
(Phase 12, Part 3.1's "llm.request" nodes).

Attached once, centrally, in app/llm_gateway.py's get_chat_model() - every
agent (ResearchAgent, AccommodationAgent, DiningAgent, ItineraryAgent) and
both orchestrators (LangGraph calls these agents directly; CrewAI's tools
close over the exact same agent objects, see
orchestration/crewai_adapter.py's module docstring) share the one
ChatLiteLLM construction path, so this is the single place that needs
instrumenting rather than four-plus call sites - the "do not create
duplicate instrumentation for the same operation" rule from Part 16.

Harmless when OTEL_ENABLED is false: get_tracer() then hands back the
OpenTelemetry API's no-op tracer, so start_span() returns a no-op span and
every method below is a cheap no-op.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from opentelemetry.trace import Status, StatusCode

from app.observability import get_tracer, record_llm_usage
from utils.logger import logger


class OTelLLMCallbackHandler(BaseCallbackHandler):
    def __init__(self, provider: Optional[str] = None):
        self._provider = provider
        self._spans: Dict[UUID, Any] = {}
        self._cms: Dict[UUID, Any] = {}

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], *, run_id: UUID, **kwargs: Any) -> None:
        model = (kwargs.get("invocation_params") or {}).get("model") or serialized.get("name")
        tracer = get_tracer()
        cm = tracer.start_as_current_span("llm.request")
        span = cm.__enter__()
        span.set_attribute("llm.model", model or "unknown")
        if self._provider:
            span.set_attribute("llm.provider", self._provider)
        span.set_attribute("llm.prompt_count", len(prompts))
        self._spans[run_id] = span
        self._cms[run_id] = cm

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        span = self._spans.pop(run_id, None)
        cm = self._cms.pop(run_id, None)
        if span is None:
            return
        try:
            usage = (response.llm_output or {}).get("token_usage") or (response.llm_output or {}).get("usage") or {}
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")
            record_llm_usage(span, model=None, provider=None, input_tokens=input_tokens, output_tokens=output_tokens)
            span.set_status(Status(StatusCode.OK))
        finally:
            if cm is not None:
                cm.__exit__(None, None, None)

    def on_llm_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        span = self._spans.pop(run_id, None)
        cm = self._cms.pop(run_id, None)
        if span is None:
            return
        try:
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
        finally:
            if cm is not None:
                cm.__exit__(type(error), error, error.__traceback__)

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        logger.warning(f"Observability: tool error in traced LLM run {run_id}: {error}")
