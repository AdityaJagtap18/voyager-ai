"""Simple character-based chunking for the RAG knowledge base (Phase 7).

No sentence/token-aware splitting — a destination guide or traveler's note is
short enough (a few paragraphs) that a fixed-size sliding window with a small
overlap is enough to keep a chunk's context from being cut off mid-thought,
without pulling in a tokenizer dependency just for this.
"""
from typing import List

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]
