"""
Embedding provider for the RAG knowledge base (Phase 7).

Uses litellm (the same library app/llm_gateway.py's chat models are built on)
so this could grow to support multiple embedding providers the same way the
chat model gateway supports multiple chat providers — today it's wired up
for OpenAI's embedding models only, which is the one provider this app
already depends on for chat.
"""
from typing import List

import litellm

from config import Config


class EmbeddingUnavailableError(RuntimeError):
    """Raised when the embedding provider isn't configured or the call failed."""


def embeddings_configured() -> bool:
    return bool(Config.OPENAI_API_KEY)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of strings. Raises EmbeddingUnavailableError if the
    configured provider's API key is missing or the call fails."""
    if not embeddings_configured():
        raise EmbeddingUnavailableError(
            f"Embedding model '{Config.EMBEDDING_MODEL}' needs OPENAI_API_KEY to be set on the server"
        )
    try:
        response = litellm.embedding(model=Config.EMBEDDING_MODEL, input=texts)
    except Exception as exc:
        raise EmbeddingUnavailableError(str(exc)) from exc
    return [item["embedding"] for item in response.data]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
