"""Factory for creating the appropriate scorer based on config."""

from __future__ import annotations

from src.config import settings
from src.scoring.base import BiasScorer


def get_scorer() -> BiasScorer:
    """Return the configured LLM scorer.

    Picks the provider based on settings.llm_provider env var.
    """
    if settings.llm_provider == "gemini":
        from src.scoring.gemini_scorer import GeminiScorer

        return GeminiScorer()
    elif settings.llm_provider == "anthropic":
        from src.scoring.anthropic_scorer import AnthropicScorer

        return AnthropicScorer()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
