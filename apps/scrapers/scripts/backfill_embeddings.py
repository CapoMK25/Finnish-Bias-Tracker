"""Backfill embeddings for articles that don't have them yet.

Run from apps/scrapers/ with venv active:

    python -m scripts.backfill_embeddings
    python -m scripts.backfill_embeddings --batch-size 100
    python -m scripts.backfill_embeddings --max-batches 5

Idempotent — articles that already have embeddings are skipped.
"""

from __future__ import annotations

import argparse
import sys

import structlog
from dotenv import load_dotenv

from src.db.articles_repo import set_article_embedding
from src.db.connection import close_pool, get_pool
from src.embeddings.vertex_embedder import VertexEmbedder

load_dotenv()

log = structlog.get_logger()


def fetch_unembedded_articles(batch_size: int = 100) -> list[dict]:
    """Get up to `batch_size` articles that don't have embeddings."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, title, body
            FROM articles
            WHERE embedding IS NULL
            ORDER BY scraped_at DESC
            LIMIT %s;
            """,
            (batch_size,),
        )
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill embeddings for articles")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Articles to fetch + embed per batch (max 250, Vertex limit)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=20,
        help="Stop after this many batches (safety limit)",
    )
    args = parser.parse_args()

    if args.batch_size > 250:
        print("--batch-size cannot exceed 250 (Vertex limit)", file=sys.stderr)
        sys.exit(2)

    embedder = VertexEmbedder()
    total_embedded = 0

    try:
        for batch_num in range(args.max_batches):
            articles = fetch_unembedded_articles(args.batch_size)
            if not articles:
                log.info("backfill_complete", total_embedded=total_embedded)
                print(f"\nDone. Embedded {total_embedded} articles total.")
                break

            log.info(
                "backfill_batch_starting",
                batch=batch_num + 1,
                count=len(articles),
            )

            embeddings = embedder.embed_batch(
                [{"title": a["title"], "body": a["body"]} for a in articles]
            )

            for article, embedding in zip(articles, embeddings, strict=True):
                set_article_embedding(article["id"], embedding)
                total_embedded += 1

            print(
                f"Batch {batch_num + 1}: embedded {len(articles)} articles "
                f"(total so far: {total_embedded})"
            )
        else:
            log.warning(
                "backfill_hit_max_batches",
                max_batches=args.max_batches,
                total_embedded=total_embedded,
                message=("Stopped at --max-batches safety limit. " "Re-run to continue."),
            )
    finally:
        close_pool()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("interrupted_by_user")
        close_pool()
        sys.exit(130)
