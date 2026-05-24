"""LLM-based bias scoring for articles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import structlog
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.prompts.bias_scoring import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)

log = structlog.get_logger()


@dataclass
class BiasScore:
    """The result of bias scoring an article."""

    bias_score: int  # -3 to +3
    confidence: float  # 0.0 to 1.0
    rationale: str
    examples: list[str]
    topic: str
    summary: str
    article_type: str
    model: str
    prompt_version: str


class LLMScorer:
    """Score articles for political bias using Claude."""

    def __init__(self, model: str | None = None) -> None:
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.llm_scoring_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def score(
        self,
        *,
        source_name: str,
        source_bias: int,
        title: str,
        body: str,
        published_at: datetime | None,
    ) -> BiasScore:
        """Score an article. Returns a BiasScore."""
        user_prompt = build_user_prompt(
            source_name=source_name,
            source_bias=source_bias,
            published_at=published_at.isoformat() if published_at else "unknown",
            title=title,
            body=body,
        )

        log.info("scoring_article", source=source_name, title=title[:80])

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = response.content[0].text  # type: ignore[union-attr]

        # Parse the JSON response defensively
        parsed = self._parse_response(raw_text)

        return BiasScore(
            bias_score=parsed["bias_score"],
            confidence=parsed["confidence"],
            rationale=parsed["rationale"],
            examples=parsed.get("examples", []),
            topic=parsed.get("topic", "other"),
            summary=parsed.get("summary", ""),
            article_type=parsed.get("article_type", "news"),
            model=self.model,
            prompt_version=PROMPT_VERSION,
        )

    @staticmethod
    def _parse_response(raw_text: str) -> dict:
        """Parse JSON from LLM response, handling common edge cases."""
        # Sometimes the LLM wraps JSON in ```json ... ``` fences despite instructions
        text = raw_text.strip()
        if text.startswith("```"):
            # Strip the first line (```json or ```) and the trailing ```
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.error("llm_response_parse_failed", raw=raw_text[:500], error=str(e))
            raise
