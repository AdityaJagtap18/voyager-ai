"""
Secret/PII redaction for span attributes (Phase 12, Part 10).

Applied unconditionally to every span before it's persisted or exported -
this is not the same switch as Config.OTEL_CAPTURE_CONTENT (that one decides
whether prompt/completion *content* is captured at all; this one guards
whatever content *is* captured against accidentally including a credential).
"""
import re
from typing import Any, Dict

# Segment-based, not substring-based: a plain substring search for "token"
# also matches inside "tokens" (plural - a count, e.g. llm.usage.total_tokens),
# which was wiping out real token-usage numbers as if they were credentials.
# Splitting on non-alphanumeric separators and checking exact segment
# equality fixes that while still catching "access_token", "api-key", etc.
_SENSITIVE_WORDS = {"authorization", "secret", "password", "token"}
_SENSITIVE_PAIRS = {("api", "key"), ("access", "key")}


def _is_sensitive_key(key: str) -> bool:
    segments = [s.lower() for s in re.split(r"[^a-zA-Z0-9]+", key) if s]
    if any(seg in _SENSITIVE_WORDS for seg in segments):
        return True
    return any((segments[i], segments[i + 1]) in _SENSITIVE_PAIRS for i in range(len(segments) - 1))

# Matches common credential-shaped substrings inside otherwise-innocuous text
# (a logged URL with a query-string key, a pasted curl command, etc.) - belt
# and suspenders on top of key-name-based redaction above.
_SECRET_VALUE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}"),  # OpenAI-style
    re.compile(r"lsv2_[a-z]+_[A-Za-z0-9]{10,}"),  # LangSmith-style
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}", re.IGNORECASE),
]

REDACTED = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _SECRET_VALUE_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a new dict: keys that look like a credential are fully
    replaced; every remaining string value is scanned for credential-shaped
    substrings. Never mutates the input (OTel's own attribute mapping may be
    read elsewhere after export)."""
    out: Dict[str, Any] = {}
    for key, value in attributes.items():
        if _is_sensitive_key(key):
            out[key] = REDACTED
        else:
            out[key] = _redact_value(value)
    return out
