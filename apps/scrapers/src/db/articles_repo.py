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


def get_recent_scored_articles(
    limit: int = 10,
    source_slug: str | None = None,
) -> list[dict]:
    """Fetch recently scored articles with their latest score, for manual audit.

    Returns the most recent N articles that have at least one score, joined
    with their source and score data. Optionally filter to a single source.

    Each result dict contains article + source + latest score fields.
    """
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        # Use DISTINCT ON to get just the latest score per article
        if source_slug:
            cur.execute(
                """
                SELECT DISTINCT ON (a.id)
                    a.id, a.url, a.title, a.published_at, a.scraped_at,
                    a.language, LENGTH(a.body) AS body_length,
                    src.slug AS source_slug, src.name AS source_name,
                    src.bias_score AS source_bias,
                    sc.bias_score, sc.confidence, sc.rationale, sc.examples,
                    sc.topic, sc.summary, a.article_type,
                    sc.model, sc.prompt_version, sc.scored_at
                FROM articles a
                JOIN sources src ON src.id = a.source_id
                JOIN article_scores sc ON sc.article_id = a.id
                WHERE src.slug = %s
                ORDER BY a.id, sc.scored_at DESC
                LIMIT %s;
                """,
                (source_slug, limit),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT ON (a.id)
                    a.id, a.url, a.title, a.published_at, a.scraped_at,
                    a.language, LENGTH(a.body) AS body_length,
                    src.slug AS source_slug, src.name AS source_name,
                    src.bias_score AS source_bias,
                    sc.bias_score, sc.confidence, sc.rationale, sc.examples,
                    sc.topic, sc.summary, a.article_type,
                    sc.model, sc.prompt_version, sc.scored_at
                FROM articles a
                JOIN sources src ON src.id = a.source_id
                JOIN article_scores sc ON sc.article_id = a.id
                ORDER BY a.id, sc.scored_at DESC
                LIMIT %s;
                """,
                (limit,),
            )

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row, strict=True)) for row in rows]


def find_similar_articles(
    article_id: UUID,
    limit: int = 10,
    max_distance: float = 0.5,
) -> list[dict]:
    """Find articles most similar to the given one by embedding distance.

    Used by clustering (#32) to seed cluster searches, and by the cluster
    API (#34) to fetch related articles for displaying.
    """
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH target AS (
                SELECT embedding FROM articles WHERE id = %s
            )
            SELECT
                a.id,
                a.title,
                a.source_id,
                a.embedding <=> t.embedding AS cosine_distance
            FROM articles a, target t
            WHERE a.id != %s
              AND a.embedding IS NOT NULL
              AND a.embedding <=> t.embedding < %s
            ORDER BY a.embedding <=> t.embedding
            LIMIT %s;
            """,
            (article_id, article_id, max_distance, limit),
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


def set_article_embedding(article_id: UUID, embedding: list[float]) -> None:
    """Set the embedding vector for an existing article.

    Writes to the pgvector vector(768) column added in #31. The pgvector
    text format is '[v1,v2,v3,...]' — psycopg accepts a plain list of
    floats and Postgres will cast it automatically via the vector type.
    """
    # Build explicit pgvector literal format
    vector_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE articles SET embedding = %s WHERE id = %s;",
            (vector_literal, article_id),
        )
        conn.commit()
        log.info(
            "embedding_persisted",
            article_id=str(article_id),
            dimensions=len(embedding),
        )


def has_embedding(article_id: UUID) -> bool:
    """Check if an article already has an embedding stored."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM articles WHERE id = %s AND embedding IS NOT NULL LIMIT 1;",
            (article_id,),
        )
        return cur.fetchone() is not None
