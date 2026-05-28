"""Main scraper runner.

Scrapes articles from a source, scores them, and persists both to Postgres.

Run with: python -m src.run
"""

from __future__ import annotations

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
from src.scrapers.yle import YleScraper

load_dotenv()

log = structlog.get_logger()


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

    # Look up source info from the database
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
            # Insert article (or fetch existing)
            article_id = upsert_article(article, source_id)
            if article_id is None:
                stats["failed"] += 1
                continue

            # Check if we should score it
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

            # Score it
            score: BiasScore = scorer.score(
                source_name=scraper.source_slug,
                source_bias=source_bias,
                title=article.title,
                body=article.body,
                published_at=article.published_at,
            )

            # Persist score
            score_id = insert_score(article_id, score)
            if score_id is None:
                stats["failed"] += 1
                continue

            stats["scored"] += 1
            stats["new"] += 1

            # Brief output for human visibility
            print(f"\n[{stats['new']}/{max_articles}] {article.title[:100]}")
            print(
                f"  Bias: {score.bias_score}  Confidence: {score.confidence:.2f}  Topic: {score.topic}"
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
    """Entry point: scrape Yle, score, persist, report stats."""
    try:
        with YleScraper() as scraper:
            stats = scrape_and_persist(scraper, max_articles=20)

        # Print summary
        print("\n" + "=" * 60)
        print("Run complete")
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
