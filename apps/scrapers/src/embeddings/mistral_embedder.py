"""Mistral embeddings for article clustering.

Uses mistral-embed by default (1024 dimensions). Embeds title + first 500
characters of body, the standard pattern for news clustering: front-loaded
reporting means the lead paragraph carries the story's distinguishing features.

Same public interface as the old Vertex embedder (embed_article / embed_batch),
so run.py and scripts/backfill_embeddings.py only need an import change.

NOTE: the articles.embedding column must be vector(1024) to match this model.
"""

from __future__ import annotations

import time

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

try:  # SDK 2.x layout
    from mistralai.client import Mistral
except ImportError:  # SDK 1.x layout
    from mistralai import Mistral

from src.config import settings

log = structlog.get_logger()

# Characters of article body included in the embedding input.
_BODY_PREFIX_CHARS = 500

# Must match the vector(N) column in apps/api/src/db/schema.ts.
EMBEDDING_DIMENSIONS = 1536

# Texts per API request. Conservative; raise after checking Mistral's limits.
_MAX_BATCH = 32


class MistralEmbedder:
    """Wrapper around the Mistral embeddings API."""

    def __init__(self, model: str | None = None) -> None:
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set in .env")
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = model or settings.mistral_embedding_model

    def _build_input(self, title: str, body: str) -> str:
        """Combine title and body prefix into one embedding input."""
        return f"{title}\n\n{body[:_BODY_PREFIX_CHARS]}"

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=30),
    )
    def _call_api(self, texts: list[str]) -> list[list[float]]:
        # Gentle pacing to avoid bursting past Mistral RPS ceilings
        time.sleep(1.2)
        try:
            response = self.client.embeddings.create(model=self.model, inputs=texts)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate limit" in err_str.lower():
                log.warning("mistral_embedding_rate_limited_retrying", error=err_str)
            raise
        return [item.embedding for item in response.data]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._call_api(texts)
        if len(vectors) != len(texts):
            raise ValueError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
        for vec in vectors:
            if len(vec) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Embedding has {len(vec)} dimensions, expected "
                    f"{EMBEDDING_DIMENSIONS}. Check MISTRAL_EMBEDDING_MODEL and "
                    "the vector(N) column size."
                )
        return vectors

    def embed_article(self, *, title: str, body: str) -> list[float]:
        """Embed a single article. Returns the vector as a list of floats."""
        text = self._build_input(title, body)
        log.info(
            "embedding_article",
            model=self.model,
            title=title[:80],
            input_chars=len(text),
        )
        embedding = self._embed([text])[0]
        log.info("article_embedded", title=title[:80], dimensions=len(embedding))
        return embedding

    def embed_batch(self, articles: list[dict[str, str]]) -> list[list[float]]:
        """Embed many articles; results are in the same order as the input.

        Args:
            articles: list of dicts with 'title' and 'body' keys
        """
        if not articles:
            return []

        texts = [self._build_input(a["title"], a["body"]) for a in articles]
        log.info("embedding_batch", model=self.model, count=len(texts))

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            embeddings.extend(self._embed(texts[start : start + _MAX_BATCH]))

        log.info("batch_embedded", count=len(embeddings))
        return embeddings
