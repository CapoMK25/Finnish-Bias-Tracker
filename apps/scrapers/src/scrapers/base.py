"""Base classes for source scrapers.

Each source has its own scraper subclass that knows:
- The source's RSS feed URL
- Any source-specific quirks (paywalls, encoding issues, RSS format oddities)
- How to map RSS items to our internal Article representation
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import ClassVar

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
            except Exception as e:
                self.log.error("entry_parse_failed", error=str(e), entry_link=entry.get("link"))


class RSSScraper(BaseScraper):
    """Concrete scraper for standard RSS-based news sources.

    The common case: an RSS feed where each <item> has a link to a full
    article page. Need to fetch the page, extract clean text via trafilatura,
    parse the published date from RFC 822, and infer article_type from
    URL path patterns.

    Subclasses set class attributes (source_slug, rss_url, language) and
    optionally override `article_type_patterns` to customize URL-based
    article type detection. No subclass should need to override
    `parse_entry()` unless the source has a truly unusual structure.

    Default `article_type_patterns` uses Finnish conventions
    (paakirjoitus, mielipide, kolumni, analyysi). Swedish-language
    scrapers (HBL) override with Swedish conventions (ledare, debatt,
    kolumn, analys). Sources with unconventional article URLs (Yle, Svenska Yle)
    override with an empty dict to disable pattern matching.

    Format: `{article_type: [list of URL substrings]}`. Each substring
    is checked with `in url`. First match wins, in dict iteration order.
    """

    #: URL substring → article_type mapping. Subclasses can override.
    article_type_patterns: ClassVar[dict[str, list[str]]] = {
        "opinion": [
            "/paakirjoitus/",
            "/paakirjoitukset/",
            "/mielipide/",
            "/kolumni/",
        ],
        "analysis": ["/analyysi/"],
    }

    def detect_article_type(self, url: str) -> str:
        """Infer article_type from URL path patterns. Defaults to 'news'."""
        for article_type, patterns in self.article_type_patterns.items():
            for pattern in patterns:
                if pattern in url:
                    return article_type
        return "news"

    def parse_published_at(self, entry: feedparser.FeedParserDict) -> datetime | None:
        """Parse the RFC 822 published date from an RSS entry, if present."""
        published = entry.get("published")
        if not published:
            return None
        try:
            return parsedate_to_datetime(published)
        except (TypeError, ValueError):
            return None

    def parse_entry(self, entry: feedparser.FeedParserDict) -> ScrapedArticle | None:
        """Default RSS entry → ScrapedArticle pipeline.

        Subclasses rarely need to override this. The pipeline is:
          1. Extract url and title from the entry
          2. Fetch the article HTML
          3. Extract clean text via trafilatura
          4. Parse the published date
          5. Detect article_type from URL patterns
          6. Assemble and return ScrapedArticle
        """
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            return None

        html = self.fetch_article_html(url)
        body = self.extract_text(html)
        if not body:
            self.log.warning("extraction_failed", url=url)
            return None

        return ScrapedArticle(
            source_slug=self.source_slug,
            url=url,
            title=title.strip(),
            body=body.strip(),
            published_at=self.parse_published_at(entry),
            language=self.language,
            article_type=self.detect_article_type(url),
        )
