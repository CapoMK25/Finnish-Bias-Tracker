"""Main scraper runner.

Scrapes articles from one source, scores them, and persists both to Postgres.

Usage:
    python -m src.run                       # default: yle
    python -m src.run --source yle
    python -m src.run --source helsingin-sanomat
    python -m src.run --source iltalehti
    python -m src.run --source ilta-sanomat
    python -m src.run --source yle --limit 5

To run all sources in a row, see scripts/scrape_all.sh
"""

from __future__ import annotations

import argparse
import sys

import structlog
from dotenv import load_dotenv
from tenacity import RetryError

from src.clustering.clustering import run_clustering_job
from src.config import settings
from src.db.articles_repo import (
    has_embedding,
    has_score_for_prompt,
    set_article_embedding,
    upsert_article,
)
from src.db.connection import close_pool
from src.db.scores_repo import insert_score
from src.db.sources_repo import get_source_bias_by_slug, get_source_id_by_slug
from src.embeddings.vertex_embedder import VertexEmbedder
from src.scoring.factory import get_scorer
from src.scoring.gemini_scorer import GeminiQuotaExhaustedError
from src.scrapers.base import BaseScraper
from src.scrapers.demokraatti import DemokraattiScraper
from src.scrapers.hbl import HblScraper
from src.scrapers.hs import HsScraper
from src.scrapers.ilta_sanomat import IltaSanomatScraper
from src.scrapers.iltalehti import IltalehtiScraper
from src.scrapers.kansan_uutiset import KansanUutisetScraper
from src.scrapers.suomen_uutiset import SuomenUutisetScraper
from src.scrapers.suomenmaa import SuomenmaaScraper
from src.scrapers.svenska_yle import SvenskaYleScraper
from src.scrapers.verkkouutiset import VerkkouutisetScraper
from src.scrapers.yle import YleScraper

load_dotenv()

log = structlog.get_logger()


# Scraper registry: maps source slug → scraper class
SCRAPERS: dict[str, type[BaseScraper]] = {
    "yle": YleScraper,
    "helsingin-sanomat": HsScraper,
    "iltalehti": IltalehtiScraper,
    "ilta-sanomat": IltaSanomatScraper,
    "demokraatti": DemokraattiScraper,
    "kansan-uutiset": KansanUutisetScraper,
    "suomen-uutiset": SuomenUutisetScraper,
    "suomenmaa": SuomenmaaScraper,
    "verkkouutiset": VerkkouutisetScraper,
    "hufvudstadsbladet": HblScraper,
    "svenska-yle": SvenskaYleScraper,
}


def scrape_and_persist(scraper: BaseScraper, max_articles: int = 20) -> tuple[dict[str, int], bool]:
    """Scrape articles from a source, score them, persist to DB.

    Returns:
        (stats, quota_exhausted) where stats is a dict with counts
        (scraped, new, duplicate, scored, skipped, failed) and
        quota_exhausted is True if the LLM rate limits exhausted retries
        mid-run, signaling the daily quota is gone for now.
    """
    stats = {
        "scraped": 0,
        "new": 0,
        "duplicate": 0,
        "scored": 0,
        "embedded": 0,
        "skipped_already_scored": 0,
        "skipped_already_embedded": 0,
        "failed": 0,
    }
    quota_exhausted = False

    source_slug = scraper.source_slug
    source_id = get_source_id_by_slug(source_slug)
    source_bias = get_source_bias_by_slug(source_slug)

    if source_id is None or source_bias is None:
        log.error("source_not_in_database", slug=source_slug)
        log.error(
            "Did you run 'npm run db:seed' from apps/api/? "
            "Source must exist in the sources table before scraping."
        )
        return stats, quota_exhausted

    scorer = get_scorer()
    embedder = VertexEmbedder()
    log.info(
        "run_started",
        source=source_slug,
        source_bias=source_bias,
        scorer=type(scorer).__name__,
        embedder=type(embedder).__name__,
        max_articles=max_articles,
    )

    for i, article in enumerate(scraper.scrape()):
        if i >= max_articles:
            break

        stats["scraped"] += 1

        try:
            article_id = upsert_article(article, source_id)
            if article_id is None:
                stats["failed"] += 1
                continue

            # --- Scoring (existing) ---
            already_scored = has_score_for_prompt(
                article_id, settings.llm_prompt_version, scorer.model
            )
            if not already_scored:
                score = scorer.score(
                    source_name=scraper.source_slug,
                    source_bias=source_bias,
                    title=article.title,
                    body=article.body,
                    published_at=article.published_at,
                )
                score_id = insert_score(article_id, score)
                if score_id is None:
                    stats["failed"] += 1
                    continue
                stats["scored"] += 1
                stats["new"] += 1
                print(f"\n[{stats['new']}/{max_articles}] {article.title[:100]}")
                print(
                    f"  Bias: {score.bias_score}  "
                    f"Confidence: {score.confidence:.2f}  Topics: {', '.join(score.topics)}"
                )
            else:
                log.info(
                    "article_already_scored",
                    title=article.title[:80],
                    prompt_version=settings.llm_prompt_version,
                )
                stats["duplicate"] += 1
                stats["skipped_already_scored"] += 1

            # --- Embedding (new) ---
            if has_embedding(article_id):
                log.info(
                    "article_already_embedded",
                    title=article.title[:80],
                )
                stats["skipped_already_embedded"] += 1
            else:
                embedding = embedder.embed_article(
                    title=article.title,
                    body=article.body,
                )
                set_article_embedding(article_id, embedding)
                stats["embedded"] += 1

        except GeminiQuotaExhaustedError as e:
            # ... existing handling ...
            # Direct signal from the scorer that quota is gone for the day
            log.error(
                "quota_exhausted",
                title=article.title[:80] if article.title else "(no title)",
                scraped_so_far=stats["scored"],
                error=str(e),
            )
            quota_exhausted = True
            break
        except RetryError as e:
            # Tenacity gave up retrying. Was it because of rate limits?
            underlying = e.last_attempt.exception() if e.last_attempt else None
            err_str = str(underlying) if underlying else ""
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                log.error(
                    "quota_exhausted",
                    title=article.title[:80] if article.title else "(no title)",
                    scraped_so_far=stats["scored"],
                    error=err_str,
                )
                quota_exhausted = True
                break
            # Retries exhausted for a non-rate-limit reason, treat as a failure
            log.error(
                "article_processing_failed",
                title=article.title[:80] if article.title else "(no title)",
                error=str(e),
                error_type="RetryError",
            )
            stats["failed"] += 1
        except Exception as e:
            log.error(
                "article_processing_failed",
                title=article.title[:80] if article.title else "(no title)",
                error=str(e),
                error_type=type(e).__name__,
            )
            stats["failed"] += 1

    return stats, quota_exhausted


def main() -> None:
    """Entry point: scrape one source, persist, report stats."""
    parser = argparse.ArgumentParser(
        prog="run",
        description="Scrape one Finnish news source and persist articles + scores.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="yle",
        choices=list(SCRAPERS.keys()),
        help="Source slug to scrape (default: yle)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max articles to scrape (default: 20)",
    )
    args = parser.parse_args()

    scraper_class = SCRAPERS[args.source]
    log.info("starting_run", source=args.source, limit=args.limit)

    quota_exhausted = False
    try:
        with scraper_class() as scraper:
            stats, quota_exhausted = scrape_and_persist(scraper, max_articles=args.limit)

        print("\n" + "=" * 60)
        print(f"Run complete: {args.source}")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key:.<30} {value}")
        print()

        if quota_exhausted:
            log.warning(
                "exiting_due_to_quota_exhaustion",
                message=(
                    "LLM daily quota exhausted. Stopping run cleanly. "
                    "Retry tomorrow (resets ~10:00 Helsinki / 00:00 PT)."
                ),
            )

    finally:
        close_pool()
    if quota_exhausted:
        sys.exit(75)  # EX_TEMPFAIL: temporary failure, e.g., rate limit exceeded


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("interrupted_by_user")
        close_pool()
        sys.exit(130)

# Run the clustering job after scraping to update clusters with any new articles.
run_clustering_job()


def run_for_source(slug: str, limit: int = 30) -> dict[str, int]:
    """
    Run scrape + score for a single source by slug.

    Wrapper around scrape_and_persist that handles scraper instantiation
    and ignores the quota_exhausted flag (the worker doesn't need it
    because BullMQ handles retry semantics independently).

    Returns the stats dict only.
    """
    if slug not in SCRAPERS:
        raise ValueError(f"Unknown source slug: {slug}. Known sources: {sorted(SCRAPERS.keys())}")

    scraper_class = SCRAPERS[slug]
    log.info("run_for_source_started", source=slug, limit=limit)

    try:
        with scraper_class() as scraper:
            stats, quota_exhausted = scrape_and_persist(scraper, max_articles=limit)
    finally:
        close_pool()

    if quota_exhausted:
        # Surface quota exhaustion as an exception so BullMQ can retry
        # tomorrow rather than silently treating the job as successful
        # with zero new articles. The worker's RetryError handling will
        # log it; the job lands in failed after 3 attempts.
        from src.scoring.gemini_scorer import GeminiQuotaExhaustedError

        raise GeminiQuotaExhaustedError(f"Quota done mid-run for {slug}. Stats: {stats}")

    return stats
