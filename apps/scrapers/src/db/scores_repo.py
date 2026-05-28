"""Repository for the article_scores table."""

from __future__ import annotations

import json
from uuid import UUID

import structlog

from src.db.connection import get_pool
from src.scoring.base import BiasScore

log = structlog.get_logger()


def insert_score(article_id: UUID, score: BiasScore) -> UUID | None:
    """Insert a bias score for an article.

    Multiple scores per article are allowed (different models, prompt versions,
    or re-scores). The latest is typically displayed; history is preserved.
    """
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO article_scores (
                    article_id, bias_score, confidence, rationale, examples,
                    topic, summary, model, prompt_version
                ) VALUES (
                    %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                )
                RETURNING id;
                """,
            (
                article_id,
                score.bias_score,
                score.confidence,
                score.rationale,
                json.dumps(score.examples),
                score.topic,
                score.summary,
                score.model,
                score.prompt_version,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        if row is None:
            log.error("insert_score_returned_no_id", article_id=str(article_id))
            return None
        log.info(
            "score_inserted",
            article_id=str(article_id),
            bias=score.bias_score,
            confidence=float(score.confidence),
        )
        return row[0]
