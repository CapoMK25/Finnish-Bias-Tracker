"""Repair: re-score articles that carry an outdated scoring prompt_version.

When PROMPT_VERSION changes in src/prompts/bias_scoring.py, every row already
scored under the old version keeps that old prompt_version forever — nothing
retroactively re-labels it. If anything downstream (the API's own
PROMPT_VERSION constant, a UI filter) compares against the new version
exactly, those old rows become invisible until they're re-scored. This
script finds and re-scores them.

Unlike rescore_unscored.py (which targets articles with NO score), every
row this script touches already has exactly one score row. Re-scoring must
REPLACE that row, not add a second one — see the REPLACE_STRATEGY note
below before running --apply for the first time.

Dry run by default: it only lists what it would do.

Usage, from apps/scrapers with the venv active:
    python -m scripts.rescore_outdated --hours 24                 # list only
    python -m scripts.rescore_outdated --hours 24 --apply         # re-score them

It stops after 5 failures in a row, so an API outage does not turn into a
pile of retries.
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg

from src.prompts.bias_scoring import PROMPT_VERSION

# DISTINCT ON a.id: some articles already carry more than one score row
# (a pre-existing bug unrelated to this script — likely a job retry
# re-scoring an article that was already scored). Without deduplicating,
# a single article with N duplicate score rows would match N times here,
# and get re-scored N times in --apply, wasting Mistral calls on the same
# article. ORDER BY a.id, sc.id DESC picks one (arbitrary which) row's
# prompt_version to report per article; it only needs to be "outdated",
# not "the latest" — the rescore itself doesn't depend on which duplicate
# was read, since insert-then-delete-others cleans up every row for that
# article regardless of which one triggered the match.
QUERY = """
    SELECT DISTINCT ON (a.id)
           a.id, s.slug, a.url, a.title, a.body, a.published_at, sc.prompt_version
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    JOIN article_scores sc ON sc.article_id = a.id
    WHERE a.scraped_at > now() - make_interval(hours => %s)
      AND sc.prompt_version <> %s
    ORDER BY a.id, sc.id DESC
    LIMIT %s
"""

MAX_CONSECUTIVE_FAILURES = 5
SECONDS_BETWEEN_CALLS = 1.2  # Mistral free tier: about one request per second

# insert_score() is a plain INSERT with no ON CONFLICT handling — the
# schema allows multiple score rows per article by design ("history is
# preserved"), so it won't collide or upsert. That means after an outdated
# row is re-scored, the article has TWO score rows (old + new) unless we
# clean up. insert_score() also opens and commits on its OWN connection
# from the pool — it does not share a transaction with this script's `conn`
# — so the insert and the cleanup delete are necessarily two separate
# commits, not one atomic step.
#
# Order matters here: insert the new score FIRST, confirm it got an id,
# THEN delete the old row(s) for that article. Doing it the other way
# around (delete, then insert) would leave the article with zero scores
# for the window between the two commits if the insert then failed — on a
# live production frontend that's strictly worse than the stale-badge
# problem this script exists to fix.


@dataclass
class Outdated:
    id: Any
    slug: str
    url: str
    title: str
    body: str
    published_at: datetime | None
    old_prompt_version: str


def find_outdated(conn: psycopg.Connection, hours: int, limit: int) -> list[Outdated]:
    with conn.cursor() as cur:
        cur.execute(QUERY, (hours, PROMPT_VERSION, limit))
        return [Outdated(*row) for row in cur.fetchall()]


def repair(
    conn: psycopg.Connection,
    rows: list[Outdated],
    *,
    apply: bool,
    rescore_one: Callable[[Outdated], None],
    pause: Callable[[float], None] = time.sleep,
    out: Callable[[str], None] = print,
) -> dict[str, int]:
    stats = {"found": len(rows), "rescored": 0, "failed": 0}

    by_old_version: dict[str, int] = {}
    for row in rows:
        by_old_version[row.old_prompt_version] = by_old_version.get(row.old_prompt_version, 0) + 1
    out(f"{len(rows)} article(s) scored under an outdated prompt_version "
        f"(target: {PROMPT_VERSION}):")
    for version, count in sorted(by_old_version.items()):
        out(f"   {count} currently at {version}")
    for row in rows:
        out(f"   to rescore    [{row.slug}] ({row.old_prompt_version}) {row.title[:80]}")
    if not apply:
        out("\nDry run: nothing changed. Add --apply to rescore them.")
        return stats

    consecutive = 0
    for row in rows:
        try:
            rescore_one(row)
            stats["rescored"] += 1
            consecutive = 0
        except Exception as e:
            stats["failed"] += 1
            consecutive += 1
            out(f"   FAILED [{row.slug}] {type(e).__name__}: {str(e)[:120]}")
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                out(f"stopping after {MAX_CONSECUTIVE_FAILURES} failures in a row (API down?)")
                break
        pause(SECONDS_BETWEEN_CALLS)

    out(f"rescored {stats['rescored']}, failed {stats['failed']}")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-score articles stored under an outdated scoring prompt_version."
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="look back this many hours (default 24)"
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="at most this many articles (default 200)"
    )
    parser.add_argument(
        "--apply", action="store_true", help="actually rescore (default: list only)"
    )
    args = parser.parse_args()

    from src.config import settings

    with psycopg.connect(settings.database_url) as conn:
        rows = find_outdated(conn, args.hours, args.limit)

        if not args.apply:
            repair(conn, rows, apply=False, rescore_one=lambda r: None)
            return

        from src.db.connection import close_pool
        from src.db.scores_repo import insert_score
        from src.db.sources_repo import get_source_bias_by_slug
        from src.scoring.factory import get_scorer

        scorer = get_scorer()

        def rescore_one(row: Outdated) -> None:
            bias = get_source_bias_by_slug(row.slug)
            score = scorer.score(
                source_name=row.slug,
                source_bias=bias,
                title=row.title,
                body=row.body,
                published_at=row.published_at,
            )
            # insert_score() commits on its own connection; if it raises,
            # nothing below runs and the old row is untouched.
            new_id = insert_score(row.id, score)
            if new_id is None:
                raise RuntimeError("insert_score returned None")
            # Now safe to drop every OTHER score row for this article — the
            # new one already exists and is committed, so there's no
            # zero-score window even if this delete fails or is interrupted.
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM article_scores WHERE article_id = %s AND id <> %s",
                    (row.id, new_id),
                )
            conn.commit()

        try:
            repair(conn, rows, apply=True, rescore_one=rescore_one)
        finally:
            close_pool()


if __name__ == "__main__":
    main()
