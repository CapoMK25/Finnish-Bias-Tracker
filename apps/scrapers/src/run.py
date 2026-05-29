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

from src.config import settings
from src.db.articles_repo import has_score_for_prompt, upsert_article
from src.db.connection import close_pool
from src.db.scores_repo import insert_score
from src.db.sources_repo import get_source_bias_by_slug, get_source_id_by_slug
from src.scoring.base import BiasScore
from src.scoring.factory import get_scorer
from src.scrapers.base import BaseScraper
from src.scrapers.hs import HsScraper
from src.scrapers.ilta_sanomat import IltaSanomatScraper
from src.scrapers.iltalehti import IltalehtiScraper
from src.scrapers.yle import YleScraper

load_dotenv()

log = structlog.get_logger()


# Scraper registry: maps source slug → scraper class
SCRAPERS: dict[str, type[BaseScraper]] = {
    "yle": YleScraper,
    "helsingin-sanomat": HsScraper,
    "iltalehti": IltalehtiScraper,
    "ilta-sanomat": IltaSanomatScraper,
}


def scrape_and_persist(scraper: BaseScraper, max_articles: int = 20) -> dict[str, int]:
    """Scrape articles from a source, score them, persist to DB.

    Returns:
        Stats dict with counts: scraped, new, duplicate, scored, skipped, failed.
    """
    stats = {
        "scraped": 0,
        "new": 0,
        "duplicate": 0,
        "scored": 0,
        "skipped_already_scored": 0,
        "failed": 0,
    }

    source_slug = scraper.source_slug
    source_id = get_source_id_by_slug(source_slug)
    source_bias = get_source_bias_by_slug(source_slug)

    if source_id is None or source_bias is None:
        log.error("source_not_in_database", slug=source_slug)
        log.error(
            "Did you run 'npm run db:seed' from apps/api/? "
            "Source must exist in the sources table before scraping."
        )
        return stats

    scorer = get_scorer()
    log.info(
        "run_started",
        source=source_slug,
        source_bias=source_bias,
        scorer=type(scorer).__name__,
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

            already_scored = has_score_for_prompt(
                article_id, settings.llm_prompt_version, scorer.model
            )

            if already_scored:
                log.info(
                    "article_already_scored",
                    title=article.title[:80],
                    prompt_version=settings.llm_prompt_version,
                )
                stats["duplicate"] += 1
                stats["skipped_already_scored"] += 1
                continue

            score: BiasScore = scorer.score(
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
                f"Confidence: {score.confidence:.2f}  Topic: {score.topic}"
            )

        except Exception as e:
            log.error(
                "article_processing_failed",
                title=article.title[:80] if article.title else "(no title)",
                error=str(e),
                error_type=type(e).__name__,
            )
            stats["failed"] += 1

    return stats


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

    try:
        with scraper_class() as scraper:
            stats = scrape_and_persist(scraper, max_articles=args.limit)

        print("\n" + "=" * 60)
        print(f"Run complete: {args.source}")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key:.<30} {value}")
        print()

    finally:
        close_pool()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("interrupted_by_user")
        close_pool()
        sys.exit(130)
