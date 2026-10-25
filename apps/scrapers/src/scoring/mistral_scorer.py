"""Mistral AI-based bias scoring."""

from __future__ import annotations

import json
import time
from datetime import datetime

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

try:  # SDK 2.x layout
    from mistralai.client import Mistral
except ImportError:  # SDK 1.x layout
    from mistralai import Mistral

from src.config import settings
from src.prompts.bias_scoring import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from src.scoring.base import BiasScore
from src.scoring.cache import cache_key, load_cached, save_cached

log = structlog.get_logger()

class MistralQuotaExhaustedError(Exception):
    """Raised when quota is exhausted"""


class _MistralRateLimited(Exception):
    """Internal marker exception for rate-limiting errors from Mistral."""


def _content_to_text(content: object) -> str | None:
    """Mistral returns message content as a string or a list of chunks."""
    if content is None:
        return None
    if isinstance(content, str):
        return content
    return "".join(getattr(chunk, "text", "") or "" for chunk in content)


class MistralScorer:
    """Score articles using Mistral's models."""

    def __init__(self, model: str | None = None) -> None:
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set in .env")
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = model or settings.mistral_scoring_model

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30))
    def score(
        self,
        *,
        source_name: str,
        source_bias: int,
        title: str,
        body: str,
        published_at: datetime | None,
    ) -> BiasScore:
        # Check cache first — avoid scoring already-processed articles
        key = cache_key(
            model=self.model,
            prompt_version=PROMPT_VERSION,
            title=title,
            body=body,
        )
        cached = load_cached(key)
        if cached is not None:
            log.info("mistral_cache_hit", source=source_name, title=title[:80])
            return cached

        # Gentle pacing to respect Mistral's free/low-tier RPS limit
        time.sleep(1.2)

        user_prompt = build_user_prompt(
            source_name=source_name,
            source_bias=source_bias,
            published_at=published_at.isoformat() if published_at else "unknown",
            title=title,
            body=body,
        )

        log.info("scoring_article", provider="mistral", source=source_name, title=title[:80])

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                log.warning("mistral_rate_limited_retrying", error=err_str)
                raise _MistralRateLimited(err_str) from e
            raise

        if not response.choices:
            raise ValueError("Mistral returned no choices")
        choice = response.choices[0]

        # Detect truncation
        reason = getattr(choice.finish_reason, "value", choice.finish_reason)
        if reason == "length":
            log.warning(
                "mistral_response_truncated",
                source=source_name,
                title=title[:80],
                finish_reason=reason,
            )
            raise ValueError("Mistral response truncated (finish_reason=length). Raise max_tokens.")

        raw_text = _content_to_text(choice.message.content)
        if not raw_text:
            raise ValueError("Mistral returned an empty response")

        parsed = self._parse_response(raw_text)

        score = BiasScore(
            bias_score=parsed["bias_score"],
            confidence=parsed["confidence"],
            rationale=parsed["rationale"],
            examples=parsed.get("examples", []),
            topics=parsed.get("topics", ["other"]),
            summary=parsed.get("summary", ""),
            article_type=parsed.get("article_type", "news"),
            model=self.model,
            prompt_version=PROMPT_VERSION,
            provider="mistral",
        )

        # Cache before returning
        save_cached(key, score)

        return score

    @staticmethod
    def _parse_response(raw_text: str) -> dict:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.error("mistral_response_parse_failed", raw=raw_text[:500], error=str(e))
            raise


def generate_cluster_title(titles: list[str]) -> str:
    """Generate a single neutral, descriptive summary headline from grouped headlines."""
    from src.config import settings

    if not titles:
        return "Untitled Event Profile"

    client = Mistral(api_key=settings.mistral_api_key)
    model = settings.mistral_scoring_model

    time.sleep(1.2)

    prompt = (
        "You are an expert, neutral news editor.\n"
        "Tasks:\n"
        "1. Analyze the following list of related news headlines.\n"
        "2. Combine them into a single, highly objective, descriptive topic headline.\n"
        "3. The headline MUST be in Finnish and be under 6 words total.\n"
        "4. Output ONLY the raw text of the headline. Do NOT include introductory words, "
        "markdown, chatty explanations, or punctuation.\n\n"
        "Headlines:\n" + "\n".join(f"- {t}" for t in titles)
    )

    try:
        response = client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50,
        )
        text = _content_to_text(response.choices[0].message.content) if response.choices else None
        if text:
            return text.strip().replace('"', "")
    except Exception as e:
        log.error("mistral_cluster_labeling_failed", error=str(e))

    return "Pending Structural Update"
