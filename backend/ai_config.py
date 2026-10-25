"""Single source of truth for AI model names, pricing and operational limits.

Pricing sourced from docs.anthropic.com/en/docs/about-claude/models/overview
on 2026-10-25. Update here when Anthropic changes prices or model IDs.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Model IDs
# ---------------------------------------------------------------------------
TUTOR_MODEL: str = os.environ.get("CC_TUTOR_MODEL", "claude-haiku-5-5")
GENERATOR_MODEL: str = "claude-sonnet-5-5"   # offline mission generation only
OPUS_MODEL: str = "claude-opus-5-5"           # offline boss-mission authoring only

# ---------------------------------------------------------------------------
# Pricing (USD per token, October 2026)
# ---------------------------------------------------------------------------
_INPUT_PRICE: dict[str, float] = {
    "claude-haiku-5-5":  0.10 / 1_000_000,
    "claude-sonnet-5-5": 2.00 / 1_000_000,
    "claude-opus-5-5":   4.00 / 1_000_000,
    "claude-fable-5-1": 10.00 / 1_000_000,
}
_OUTPUT_PRICE: dict[str, float] = {
    "claude-haiku-5-5":   0.50 / 1_000_000,
    "claude-sonnet-5-5": 10.00 / 1_000_000,
    "claude-opus-5-5":   20.00 / 1_000_000,
    "claude-fable-5-1":  50.00 / 1_000_000,
}
_FALLBACK_INPUT  = 0.10 / 1_000_000
_FALLBACK_OUTPUT = 0.50 / 1_000_000


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the USD cost for one API call rounded to 8 decimal places."""
    ip = _INPUT_PRICE.get(model, _FALLBACK_INPUT)
    op = _OUTPUT_PRICE.get(model, _FALLBACK_OUTPUT)
    return round(ip * input_tokens + op * output_tokens, 8)


# ---------------------------------------------------------------------------
# Operational limits (all overridable via environment variables)
# ---------------------------------------------------------------------------
TUTOR_TIMEOUT: float = float(os.environ.get("CC_TUTOR_TIMEOUT", "8"))
DEFAULT_DAILY_PLAYER_CAP: int = int(os.environ.get("CC_DAILY_PLAYER_CAP", "5"))
DEFAULT_DAILY_BUDGET_USD: float = float(os.environ.get("CC_DAILY_BUDGET_USD", "1.00"))
