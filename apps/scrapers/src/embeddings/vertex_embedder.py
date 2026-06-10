"""Vertex AI embeddings for article clustering.

Uses text-multilingual-embedding-002 by default. Handles Finnish and
Swedish content okay, which matters because HBL and Svenska Yle
publish in Swedish while all other sources publish in Finnish —
clusters can span both languages.

Uses the same google-genai SDK and Application Default Credentials
as the Gemini scorer. One single vendor for everything via GCP.

Embeds title + first 500 characters of the body. This is the standard
pattern for news article clustering — front-loaded reporting structure
means the lead paragraph contains the story's distinguishing features.
"""

from __future__ import annotations

import structlog
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

log = structlog.get_logger()


# How many characters of the article body to include in the embedding input.
# News articles front-load important information; the first ~500 chars
# typically contain the distinguishing features for clustering.
# this can be examined in the future since this is not the case all the time, especially for nicher sources.
_BODY_PREFIX_CHARS = 500


class VertexEmbedder:
    """Wrapper around the Vertex AI embedding API."""

    def __init__(self, model: str | None = None) -> None:
        if not settings.gcp_project_id:
            raise ValueError(
                "GCP_PROJECT_ID is not set. The Vertex embedder uses "
                "Application Default Credentials, same as the Gemini scorer. "
                "Run 'gcloud auth application-default login' and ensure "
                "GCP_PROJECT_ID is in .env."
            )

        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
        )
        self.model = model or settings.vertex_embedding_model

    def _build_input(self, title: str, body: str) -> str:
        """Combine title and body prefix into a single embedding input.

        Format: "<title>\\n\\n<first 500 chars of body>"
        """
        prefix = body[:_BODY_PREFIX_CHARS]
        return f"{title}\n\n{prefix}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
    )
    def embed_article(self, *, title: str, body: str) -> list[float]:
        """Embed a single article. Returns the vector as a list of floats."""
        text = self._build_input(title, body)

        log.info(
            "embedding_article",
            model=self.model,
            title=title[:80],
            input_chars=len(text),
        )

        result = self.client.models.embed_content(
            model=self.model,
            contents=[text],
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
            ),
        )

        embedding = result.embeddings[0].values
        log.info(
            "article_embedded",
            title=title[:80],
            dimensions=len(embedding),
        )
        return embedding

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
    )
    def embed_batch(
        self, articles: list[dict[str, str]]
    ) -> list[list[float]]:
        """Embed many articles in a single API call.

        Args:
            articles: list of dicts with 'title' and 'body' keys

        Returns:
            list of embeddings in the same order as the input

        Vertex AI accepts up to 250 texts per batch for the embedding
        endpoint. For backfilling many historical articles, prefer this
        over single-article calls — same total cost, far less HTTP
        overhead.
        """
        if not articles:
            return []

        if len(articles) > 250:
            raise ValueError(
                f"Vertex batch limit is 250, got {len(articles)}. "
                "Chunk your input before calling embed_batch()."
            )

        texts = [self._build_input(a["title"], a["body"]) for a in articles]

        log.info(
            "embedding_batch",
            model=self.model,
            count=len(texts),
            total_chars=sum(len(t) for t in texts),
        )

        result = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
            ),
        )

        embeddings = [e.values for e in result.embeddings]
        log.info(
            "batch_embedded",
            count=len(embeddings),
        )
        return embeddings