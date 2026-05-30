"""Scraper for Verkkouutiset (verkkouutiset slug).

Online newspaper affiliated with the National Coalition Party (Kokoomus).
Bias classification: +1 (party-organ tier, right).
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from src.scrapers.base import BaseScraper, ScrapedArticle


class VerkkouutisetScraper(BaseScraper):
    source_slug = "verkkouutiset"
    rss_url = "https://www.verkkouutiset.fi/feed/"
    language = "fi"

    def parse_entry(self, entry: feedparser.FeedParserDict) -> ScrapedArticle | None:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            return None

        html = self.fetch_article_html(url)
        body = self.extract_text(html)
        if not body:
            self.log.warning("extraction_failed", url=url)
            return None

        published_at: datetime | None = None
        if entry.get("published"):
            try:
                published_at = parsedate_to_datetime(entry.published)
            except (TypeError, ValueError):
                published_at = None

        article_type = "news"
        if "/paakirjoitus/" in url or "/mielipide/" in url or "/kolumni/" in url:
            article_type = "opinion"
        elif "/analyysi/" in url:
            article_type = "analysis"

        return ScrapedArticle(
            source_slug=self.source_slug,
            url=url,
            title=title.strip(),
            body=body.strip(),
            published_at=published_at,
            language=self.language,
            article_type=article_type,
        )
