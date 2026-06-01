"""Scraper for Svenska Yle (svenska-yle slug).

Swedish-language service of Yle, Finland's public broadcaster.
Bias classification: -1 (public service, center-left perception).
Language: Swedish (sv).

Feed note: Yle's standard /feed/ and /rss URLs do NOT return RSS feeds
on the Swedish service. The canonical feed is advertised in the homepage
<link rel="alternate"> tag and lives at /rss/senaste-nytt.

Article URL note: feed entries link to canonical URLs on the yle.fi
domain (e.g., https://yle.fi/a/7-10099490?origin=rss), not section
paths on svenska.yle.fi. As a result, article_type cannot be inferred
from URL structure; everything is classified as "news" by default.
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from src.scrapers.base import BaseScraper, ScrapedArticle


class SvenskaYleScraper(BaseScraper):
    source_slug = "svenska-yle"
    rss_url = "https://svenska.yle.fi/rss/senaste-nytt"
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

        # Yle URLs are opaque (/a/<id>); article_type cannot be inferred
        # from URL structure. Default to news; opinion/analysis would
        # require parsing article metadata from the page HTML, which is
        # out of scope for this scraper.
        article_type = "news"

        return ScrapedArticle(
            source_slug=self.source_slug,
            url=url,
            title=title.strip(),
            body=body.strip(),
            published_at=published_at,
            language=self.language,
            article_type=article_type,
        )
