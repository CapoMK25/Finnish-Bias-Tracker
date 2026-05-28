"""Repository for the sources table."""

from __future__ import annotations

from uuid import UUID

import structlog

from src.db.connection import get_pool

log = structlog.get_logger()


def get_source_id_by_slug(slug: str) -> UUID | None:
    """Look up a source's UUID by slug. Returns None if not found."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM sources WHERE slug = %s LIMIT 1;", (slug,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]


def get_source_bias_by_slug(slug: str) -> int | None:
    """Look up a source's bias score by slug. Returns None if not found."""
    pool = get_pool()
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT bias_score FROM sources WHERE slug = %s LIMIT 1;", (slug,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0]
