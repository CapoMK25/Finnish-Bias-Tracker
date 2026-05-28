"""Repository for the articles table.

Handles deduplication via two strategies:
1. URL uniqueness (caught by the unique index on articles.url)
2. Content hash uniqueness (caught by the unique index on articles.content_hash)
   — catches the same article republished under a different URL.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from src.db.connection import get_pool
from src.scrapers.base import ScrapedArticle

log = structlog.get_logger()


def upsert_article(article: ScrapedArticle, source_id: UUID) -> UUID | None:
    """Insert an article if it doesn't exist (by url or content_hash).

    Returns:
        - UUID of the inserted article if new
        - UUID of the existing article if duplicate (caller can decide whether to skip scoring)
        - None on unexpected error
    """
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        # First, check if article already exists by URL
        cur.execute(
            "SELECT id FROM articles WHERE url = %s LIMIT 1;",
            (article.url,),
        )
        existing = cur.fetchone()
        if existing is not None:
            log.debug("article_already_exists_by_url", url=article.url)
            return existing[0]

        # Or by content hash (same content, different URL)
        cur.execute(
            "SELECT id FROM articles WHERE content_hash = %s LIMIT 1;",
            (article.content_hash,),
        )
        existing = cur.fetchone()
        if existing is not None:
            log.debug(
                "article_already_exists_by_content_hash",
                url=article.url,
                hash=article.content_hash[:16],
            )
            return existing[0]

        # Insert new article
        cur.execute(
            """
                INSERT INTO articles (
                    source_id, url, title, body, published_at,
                    content_hash, language, article_type
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
                """,
            (
                source_id,
                article.url,
                article.title,
                article.body,
                article.published_at,
                article.content_hash,
                article.language,
                article.article_type,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        if row is None:
            log.error("insert_article_returned_no_id", url=article.url)
            return None
        log.info("article_inserted", url=article.url, id=str(row[0]))
        return row[0]


def has_score_for_prompt(article_id: UUID, prompt_version: str, model: str) -> bool:
    """Check if an article has already been scored with a given prompt + model.

    Used to skip re-scoring articles when re-running the pipeline.
    """
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT 1 FROM article_scores
                WHERE article_id = %s AND prompt_version = %s AND model = %s
                LIMIT 1;
                """,
            (article_id, prompt_version, model),
        )
        return cur.fetchone() is not None
