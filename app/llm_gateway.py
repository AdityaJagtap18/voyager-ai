"""
Model gateway (Phase 5).

Before this, every agent built its own `ChatOpenAI(...)` directly — swapping
providers meant editing four files. This module is the one place that picks
and constructs a chat model, built on LiteLLM's unified `model` string
convention (e.g. "gpt-4o-mini", "anthropic/claude-3-5-sonnet-20241022",
"ollama/llama3") so the same agent code can run against OpenAI, Anthropic,
Gemini, or a local Ollama model with no change beyond which id is selected.

Agents still get back a LangChain-compatible chat model (ChatLiteLLM), so the
existing `prompt | self.llm` LCEL chains in research_agent.py etc. are
untouched — only the construction line changes.
"""
from dataclasses import dataclass
from typing import Dict, Optional

from langchain_litellm import ChatLiteLLM

from config import Config


@dataclass(frozen=True)
class ModelInfo:
    id: str  # the litellm model string passed straight through to ChatLiteLLM
    label: str
    provider: str  # openai | anthropic | google | ollama
    context_window: int
    local: bool = False
    requires_env: Optional[str] = None  # env var that must be set for this model to work


MODEL_REGISTRY: Dict[str, ModelInfo] = {
    # gpt-3.5-turbo was removed from this registry: OpenAI deprecated it
    # (litellm.NotFoundError on every real call) — discovered via live testing
    # during Phase 3's planner-fusion work. gpt-4o-mini is the equivalent
    # cheap/fast tier that's still live.
    "gpt-4o-mini": ModelInfo("gpt-4o-mini", "GPT-4o mini", "openai", 128000, requires_env="OPENAI_API_KEY"),
    "gpt-4o": ModelInfo("gpt-4o", "GPT-4o", "openai", 128000, requires_env="OPENAI_API_KEY"),
    "anthropic/claude-3-5-sonnet-20241022": ModelInfo(
        "anthropic/claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", "anthropic", 200000, requires_env="ANTHROPIC_API_KEY"
    ),
    "gemini/gemini-1.5-flash": ModelInfo(
        "gemini/gemini-1.5-flash", "Gemini 1.5 Flash", "google", 1000000, requires_env="GOOGLE_API_KEY"
    ),
    "ollama/llama3": ModelInfo("ollama/llama3", "Llama 3 (Ollama, local)", "ollama", 8192, local=True),
}

DEFAULT_MODEL = "gpt-4o-mini"


def is_configured(model_id: str) -> bool:
    """Whether the credentials/server this model needs are present.

    Local (Ollama) models report configured=True since they need no API key —
    this does not check that an Ollama server is actually reachable; that is
    a health check for a later phase (Section 6.1's "health checks" item).
    """
    info = MODEL_REGISTRY.get(model_id)
    if info is None:
        return False
    if info.local:
        return True
    if not info.requires_env:
        return True
    return bool(getattr(Config, info.requires_env, None))


def resolve_model(model_id: Optional[str]) -> str:
    """Pick the model to actually use: the requested one if known, else the
    configured default (OPENAI_MODEL), else the hardcoded fallback."""
    if model_id and model_id in MODEL_REGISTRY:
        return model_id
    if Config.OPENAI_MODEL in MODEL_REGISTRY:
        return Config.OPENAI_MODEL
    return DEFAULT_MODEL


def get_chat_model(model_id: Optional[str] = None, temperature: Optional[float] = None) -> ChatLiteLLM:
    """Build a LangChain-compatible chat model for the resolved model id.

    No api_key is passed explicitly: Config's `load_dotenv()` has already put
    OPENAI_API_KEY/ANTHROPIC_API_KEY/GOOGLE_API_KEY into the process
    environment, and litellm reads the right one itself based on the model
    string's provider prefix.
    """
    resolved = resolve_model(model_id)
    info = MODEL_REGISTRY.get(resolved)
    callbacks = []
    if Config.OTEL_ENABLED:
        # Phase 12: one callback handler per chat model, not a process-wide
        # singleton - run_id-keyed state (see OTelLLMCallbackHandler) still
        # needs isolating per model instance so concurrent trips can't cross
        # streams, and a chat model is cheap to construct either way.
        from app.observability.langchain_callback import OTelLLMCallbackHandler

        callbacks.append(OTelLLMCallbackHandler(provider=info.provider if info else None))

    return ChatLiteLLM(
        model=resolved,
        temperature=temperature if temperature is not None else Config.OPENAI_TEMPERATURE,
        max_retries=Config.MAX_RETRIES,
        callbacks=callbacks or None,
    )
