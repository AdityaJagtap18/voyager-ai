"""
Secret/PII redaction for span attributes (Phase 12, Part 10).

Applied unconditionally to every span before it's persisted or exported -
this is not the same switch as Config.OTEL_CAPTURE_CONTENT (that one decides
whether prompt/completion *content* is captured at all; this one guards
whatever content *is* captured against accidentally including a credential).
"""
import re
from typing import Any, Dict

_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|secret|password|token|access[_-]?key|client[_-]?secret)", re.IGNORECASE
)

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
        if _SECRET_KEY_PATTERN.search(key):
            out[key] = REDACTED
        else:
            out[key] = _redact_value(value)
    return out
