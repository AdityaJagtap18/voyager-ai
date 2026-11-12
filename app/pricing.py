"""
Public per-token USD pricing for models in llm_gateway.MODEL_REGISTRY (Phase
12 / "Tokenomics"), used only to turn real token counts already recorded on
spans into an estimated dollar cost - never a substitute for a provider's
actual invoice. Sourced from each provider's published pricing page; prices
change over time, so treat this as an estimate and update the table when a
provider repriced a model you use.

Deliberately NOT keyed by every model id in MODEL_REGISTRY: a model with no
entry here returns None from estimate_cost_usd() rather than a guessed price.
"""
from typing import Dict, NamedTuple, Optional


class TokenPricing(NamedTuple):
    input_per_million: float  # USD per 1,000,000 input tokens
    output_per_million: float  # USD per 1,000,000 output tokens


PRICING_USD_PER_MILLION_TOKENS: Dict[str, TokenPricing] = {
    "gpt-4o-mini": TokenPricing(0.15, 0.60),
    "gpt-4o": TokenPricing(2.50, 10.00),
    "anthropic/claude-3-5-sonnet-20241022": TokenPricing(3.00, 15.00),
    "gemini/gemini-1.5-flash": TokenPricing(0.075, 0.30),
    "ollama/llama3": TokenPricing(0.0, 0.0),  # local inference, no per-token billing
}


def estimate_cost_usd(model: Optional[str], input_tokens: Optional[float], output_tokens: Optional[float]) -> Optional[float]:
    """Returns None (not 0) when the model has no pricing entry or either
    token count is missing - a missing cost must never be displayed as free."""
    if not model or model not in PRICING_USD_PER_MILLION_TOKENS:
        return None
    if input_tokens is None or output_tokens is None:
        return None
    pricing = PRICING_USD_PER_MILLION_TOKENS[model]
    return (input_tokens / 1_000_000) * pricing.input_per_million + (output_tokens / 1_000_000) * pricing.output_per_million
