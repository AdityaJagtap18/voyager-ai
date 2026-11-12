"""
Voyager Configuration
Loads environment variables and application settings
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration settings"""
    
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    # Phase 5: additional model providers the gateway (app/llm_gateway.py) can
    # route to. None of these are required — only set the ones you want to try.
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

    # Phase 7: embedding model for the RAG knowledge base (app/rag). Only
    # OpenAI-compatible embedding models are wired up today, so this still
    # needs OPENAI_API_KEY above — a future phase can extend app/rag/embeddings.py
    # the same way app/llm_gateway.py supports multiple chat providers.
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Application Settings
    APP_NAME = "Voyager"
    APP_VERSION = "0.1.0"
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # Agent Settings
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "120"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    # Observability (Phase 12): all optional, all default to off/unset so the
    # app behaves exactly as before if none of this is configured. See
    # app/observability/__init__.py for how these are actually used - this
    # class only reads env vars, same as everything else here.
    OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "voyager-ai")
    OTEL_ENVIRONMENT = os.getenv("OTEL_ENVIRONMENT", "development")
    # Endpoint for an OTLP collector (e.g. http://localhost:4318 for HTTP,
    # http://localhost:4317 for gRPC). Unset => traces/metrics are recorded
    # in-process (for the Observability UI's own trace store) but not
    # exported anywhere external.
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_EXPORTER_OTLP_PROTOCOL = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    # "always_on" | "always_off" | "traceidratio"
    OTEL_TRACES_SAMPLER = os.getenv("OTEL_TRACES_SAMPLER", "always_on")
    OTEL_TRACES_SAMPLER_ARG = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0"))

    # LangSmith's own SDK reads LANGSMITH_TRACING/LANGSMITH_API_KEY/
    # LANGSMITH_PROJECT itself (it's what actually turns LangChain/LangGraph's
    # built-in tracing on) - mirrored into Config so app code and tests can
    # check status without re-parsing os.environ, but these are the exact
    # names LangSmith expects, not a Voyager-specific convention.
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "voyager-ai")
    LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    PHOENIX_ENABLED = os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
    # Local Phoenix (phoenix.launch_app()) listens on this by default; set to
    # a remote Phoenix's OTLP endpoint instead to use a non-local instance.
    PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
    PHOENIX_PROJECT_NAME = os.getenv("PHOENIX_PROJECT_NAME", "voyager-ai")
    # Phoenix 21.x enables login/auth by default, which also protects its
    # OTLP collector - without this, span export gets a 401 even though the
    # endpoint is otherwise reachable. Generated under Settings > API Keys
    # in the Phoenix UI; optional (only needed when the Phoenix instance has
    # auth enabled, which is the default for this image).
    PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")

    # Phase 12: whether full prompt/completion text is captured in traces at
    # all (vs. metadata-only - model, token counts, duration). Separate from
    # per-field redaction (app/observability/redaction.py), which always runs
    # regardless of this flag - this is a coarser on/off switch for people who
    # don't want prompt content leaving the process under any backend.
    OTEL_CAPTURE_CONTENT = os.getenv("OTEL_CAPTURE_CONTENT", "true").lower() == "true"

    @classmethod
    def validate(cls):
        """Check if required settings exist"""
        if not cls.OPENAI_API_KEY:
            raise ValueError(" OPENAI_API_KEY not found! Add it to .env file")
        
        print(f"   Configuration loaded successfully")
        print(f"   Model: {cls.OPENAI_MODEL}")
        print(f"   Temperature: {cls.OPENAI_TEMPERATURE}")
        return True

