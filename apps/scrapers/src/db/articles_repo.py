"""Repository for the articles table.

Handles deduplication via two strategies:
1. URL uniqueness (caught by the unique index on articles.url)
2. Content hash uniqueness (caught by the unique index on articles.content_hash)
   — catches the same article republished under a different URL.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
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
                    sc.topics, sc.summary, a.article_type,
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
                    sc.topics, sc.summary, a.article_type,
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


def get_recent_embeddings(hours: int = 48) -> list[dict]:
    """Fetch articles and their embeddings from the rolling window."""
    since_time = datetime.utcnow() - timedelta(hours=hours)
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, embedding
            FROM articles
            WHERE embedding IS NOT NULL
              AND scraped_at >= %s;
            """,
            (since_time,),
        )
        rows = cur.fetchall()

        results = []
        for row in rows:
            emb_str = row[2]
            # Handle string-format arrays if the driver returns them as plain text
            if isinstance(emb_str, str):
                emb = [float(x) for x in emb_str.strip("[]").split(",")]
            else:
                emb = list(emb_str)
            results.append({"id": row[0], "title": row[1], "embedding": emb})
        return results


def update_cluster_assignments(
    assignments: dict[UUID, UUID | None], new_clusters: list[UUID]
) -> None:
    """Atomically insert new cluster records and update article associations."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            if not assignments:
                return

            # 1. Register new clusters in your existing clusters table
            # Added both first_seen_at and last_seen_at to clear all NOT NULL constraints
            for cluster_id in new_clusters:
                cur.execute(
                    """
                    INSERT INTO clusters (id, title, first_seen_at, last_seen_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (cluster_id, "Pending Title Assignment"),
                )

            # 2. Map articles to their assigned clusters (or NULL if classified as noise)
            for article_id, cluster_id in assignments.items():
                cur.execute(
                    "UPDATE articles SET cluster_id = %s WHERE id = %s;",
                    (cluster_id, article_id),
                )
        conn.commit()


def get_pending_clusters() -> list[dict]:
    """Fetch recent clusters missing final evaluations and summaries."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.id as cluster_id,
                array_agg(a.title) as article_titles,
                array_agg(s.bias_score) as bias_scores
            FROM clusters c
            JOIN articles a ON a.cluster_id = c.id
            JOIN sources s ON a.source_id = s.id
            WHERE c.title = 'Pending Title Assignment'
            GROUP BY c.id;
            """
        )
        rows = cur.fetchall()
        return [
            {"id": row[0], "titles": row[1], "biases": [int(b) for b in row[2] if b is not None]}
            for row in rows
        ]


def save_cluster_metadata(
    cluster_id: UUID, title: str, entropy: float, blindspot: str, distribution: dict
) -> None:
    """Commit LLM derived labels and calculated entropy statistics back to storage."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE clusters
            SET
                title = %s,
                entropy = %s,
                blindspot_label = %s,
                bias_distribution = %s,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (title, entropy, blindspot, json.dumps(distribution), cluster_id),
        )
        conn.commit()


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
