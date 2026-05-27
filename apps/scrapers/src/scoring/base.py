"""Base classes and protocols for LLM-based bias scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class BiasScore:
    """The result of bias scoring an article. Provider-agnostic."""

    bias_score: int  # -3 to +3
    confidence: float  # 0.0 to 1.0
    rationale: str
    examples: list[str]
    topic: str
    summary: str
    article_type: str
    model: str
    prompt_version: str
    provider: str  # "anthropic" | "gemini"


class BiasScorer(Protocol):
    """Protocol for any LLM-based bias scorer.

    Implementations must be swappable via config. The orchestration code
    should depend on this protocol, not on any specific provider.
    """

    def score(
        self,
        *,
        source_name: str,
        source_bias: int,
        title: str,
        body: str,
        published_at: datetime | None,
    ) -> BiasScore:
        """Score an article for political bias.

        Args:
            source_name: Display name of the source (e.g., "Yle Uutiset")
            source_bias: Source-level bias score (-3 to +3)
            title: Article headline
            body: Article body text (already extracted, clean)
            published_at: When the article was published

        Returns:
            A BiasScore with bias direction, confidence, rationale, and metadata.

        Raises:
            Provider-specific exceptions on API errors. Caller should handle retries.
        """
        ...
