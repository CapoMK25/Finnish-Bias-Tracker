"""Scraper for Hufvudstadsbladet (hufvudstadsbladet slug).

Swedish-language Finnish daily newspaper, owned by KSF Media.
Often editorially aligned with the Swedish People's Party (RKP).
Bias classification: -1 (center-liberal, mainstream).
Language: Swedish (sv).
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from src.scrapers.base import BaseScraper, ScrapedArticle


class HblScraper(BaseScraper):
    source_slug = "hufvudstadsbladet"
    rss_url = "https://www.hbl.fi/feed/"
    language = "sv"

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
        if "/ledare/" in url or "/opinion/" in url or "/debatt/" in url or "/kolumn/" in url:
            article_type = "opinion"
        elif "/analys/" in url:
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
