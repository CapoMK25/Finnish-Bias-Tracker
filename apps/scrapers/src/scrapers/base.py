"""Base classes for source scrapers.

Each source has its own scraper subclass that knows:
- The source's RSS feed URL
- Any source-specific quirks (paywalls, encoding issues, RSS format oddities)
- How to map RSS items to our internal Article representation
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import feedparser
import httpx
import structlog
import trafilatura
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

log = structlog.get_logger()


@dataclass
class ScrapedArticle:
    """A scraped article, before storage."""

    source_slug: str
    url: str
    title: str
    body: str
    published_at: datetime | None
    language: str = "fi"
    article_type: str = "news"

    @property
    def content_hash(self) -> str:
        """sha256 of body, for deduplication."""
        return hashlib.sha256(self.body.encode("utf-8")).hexdigest()


class BaseScraper(ABC):
    """Abstract base class for source scrapers."""

    source_slug: str
    rss_url: str
    language: str = "fi"

    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": settings.scraper_user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        self.log = log.bind(scraper=self.source_slug)

    def __enter__(self) -> BaseScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_feed(self) -> feedparser.FeedParserDict:
        """Fetch and parse the RSS feed."""
        self.log.info("fetching_feed", url=self.rss_url)
        response = self.client.get(self.rss_url)
        response.raise_for_status()
        return feedparser.parse(response.content)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_article_html(self, url: str) -> str:
        """Fetch raw HTML for an article."""
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def extract_text(self, html: str) -> str | None:
        """Extract clean article text from HTML.

        Uses trafilatura which is best-in-class for this.
        """
        return trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            target_language=self.language,
        )

    @abstractmethod
    def parse_entry(self, entry: feedparser.FeedParserDict) -> ScrapedArticle | None:
        """Convert an RSS entry into a ScrapedArticle.

        Each source overrides this to handle quirks.
        Return None to skip an entry (e.g., paywalled, wrong type).
        """
        ...

    def scrape(self) -> Iterator[ScrapedArticle]:
        """Main entry point — yields scraped articles."""
        feed = self.fetch_feed()
        self.log.info("feed_fetched", entry_count=len(feed.entries))

        for entry in feed.entries:
            try:
                article = self.parse_entry(entry)
                if article is None:
                    continue
                if not article.body or len(article.body) < 100:
                    self.log.warning("article_too_short", url=article.url)
                    continue
                yield article
            except Exception as e:  # noqa: BLE001
                self.log.error("entry_parse_failed", error=str(e), entry_link=entry.get("link"))
