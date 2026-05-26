"""Main scraper runner.

Run with: python -m src.run
"""

from __future__ import annotations

import structlog
from dotenv import load_dotenv

from src.scoring.llm_scorer import LLMScorer
from src.scrapers.yle import YleScraper

load_dotenv()

log = structlog.get_logger()


def main() -> None:
    """Scrape Yle, score the first 3 articles, print results.

    This is the M1 milestone proof — verifies the full pipeline end-to-end.
    Once this works, expand to all sources and queue-driven workers.
    """
    log.info("scraper_run_started")

    scorer = LLMScorer()

    with YleScraper() as scraper:
        for i, article in enumerate(scraper.scrape()):
            if i >= 3:
                break

            log.info(
                "article_scraped",
                title=article.title[:80],
                body_length=len(article.body),
            )

            score = scorer.score(
                source_name="Yle",
                source_bias=-1,  # From sources.md
                title=article.title,
                body=article.body,
                published_at=article.published_at,
            )

            print(f"\n{'=' * 80}")
            print(f"Title: {article.title}")
            print(f"URL: {article.url}")
            print(f"Bias: {score.bias_score} (confidence: {score.confidence:.2f})")
            print(f"Topic: {score.topic}")
            print(f"Type: {score.article_type}")
            print(f"\nRationale: {score.rationale}")
            print("\nExamples:")
            for example in score.examples:
                print(f"  - {example}")
            print(f"\nSummary: {score.summary}")

    log.info("scraper_run_completed")


if __name__ == "__main__":
    main()
