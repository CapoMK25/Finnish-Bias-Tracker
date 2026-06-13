"""Google Gemini-based bias scoring."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import structlog
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.prompts.bias_scoring import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from src.scoring.base import BiasScore
from src.scoring.cache import cache_key, load_cached, save_cached

log = structlog.get_logger()


class GeminiQuotaExhaustedError(Exception):
    """Raised when the Gemini rate limits exhaust retries quota is done.

    Signals upstream callers that further API calls in the current window
    will likely fail. The caller should stop the current batch rather than
    burning more retries.
    """


class _GeminiRateLimited(Exception):
    """Internal marker for rate-limit failures.

    Tenacity will retry on this. After retries exhaust, the outer caller
    inspects RetryError to distinguish rate-limit exhaustion from other
    failures and raises GeminiQuotaExhaustedError accordingly.
    """


# Module-level rate limit tracking
_last_call_time = 0.0
_MIN_INTERVAL_SECONDS = 1.0  # Vertex AI compatible now instead of the free tier on Gemini


def _throttle() -> None:
    """Block until enough time has passed since the last Gemini call."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL_SECONDS:
        sleep_for = _MIN_INTERVAL_SECONDS - elapsed
        log.info("rate_limit_throttle", sleeping=sleep_for)
        time.sleep(sleep_for)
    _last_call_time = time.time()


def _extract_retry_after(error_message: str) -> float:
    """Extract retry delay from a Gemini 429 error message."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_message)
    if match:
        return float(match.group(1))
    return 30.0


class GeminiScorer:
    """Score articles using Google's Gemini models."""

    def __init__(self, model: str | None = None) -> None:
        if not settings.gcp_project_id:
            raise ValueError(
                "GCP_PROJECT_ID is not set. The Gemini scorer uses Vertex AI "
                "with Application Default Credentials. Run 'gcloud auth "
                "application-default login' and ensure GCP_PROJECT_ID is in .env."
            )
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.model = model or settings.gemini_scoring_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=15, max=60))
    def score(
        self,
        *,
        source_name: str,
        source_bias: int,
        title: str,
        body: str,
        published_at: datetime | None,
    ) -> BiasScore:
        # Check cache first — never spend quota on already-scored articles
        key = cache_key(
            model=self.model,
            prompt_version=PROMPT_VERSION,
            title=title,
            body=body,
        )
        cached = load_cached(key)
        if cached is not None:
            log.info("gemini_cache_hit", source=source_name, title=title[:80])
            return cached

        _throttle()

        user_prompt = build_user_prompt(
            source_name=source_name,
            source_bias=source_bias,
            published_at=published_at.isoformat() if published_at else "unknown",
            title=title,
            body=body,
        )

        log.info("scoring_article", provider="gemini", source=source_name, title=title[:80])

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )
        except ClientError as e:
            err_str = str(e)
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                retry_after = _extract_retry_after(err_str)
                log.warning("gemini_rate_limited", retry_after=retry_after)
                time.sleep(retry_after + 2)
                raise _GeminiRateLimited(err_str) from e
            raise

        # Detect truncation
        if response.candidates and response.candidates[0].finish_reason:
            reason = response.candidates[0].finish_reason
            if reason.name == "MAX_TOKENS":
                log.warning(
                    "gemini_response_truncated",
                    source=source_name,
                    title=title[:80],
                    finish_reason=reason.name,
                )
                raise ValueError("Gemini response truncated (MAX_TOKENS). Raise max_output_tokens.")

        raw_text = response.text
        if raw_text is None:
            raise ValueError("Gemini returned an empty response")

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
            provider="gemini",
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
            log.error("gemini_response_parse_failed", raw=raw_text[:500], error=str(e))
            raise


def generate_cluster_title(titles: list[str]) -> str:
    """Generate a single neutral, descriptive summary headline from grouped headlines."""
    from src.config import settings

    if not titles:
        return "Untitled Event Profile"

    # Reuse configuration exactly like the main Scorer
    client = genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )
    model = settings.gemini_scoring_model

    _throttle()

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
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50,
            ),
        )
        if response.text:
            return response.text.strip().replace('"', "")
    except Exception as e:
        log.error("gemini_cluster_labeling_failed", error=str(e))

    return "Pending Structural Update"
