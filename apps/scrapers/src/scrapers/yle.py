"""Scraper for Yle (yle.fi).

Yle is Finland's public broadcaster. Clean RSS feed, full content at the
linked URL, no paywall. Article URLs are opaque (yle.fi/a/<id>) so
article_type cannot be inferred from path; everything defaults to 'news'.
"""

from __future__ import annotations

from typing import ClassVar

from src.scrapers.base import RSSScraper


class YleScraper(RSSScraper):
    source_slug = "yle"
    rss_url = "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss"
    language = "fi"
    article_type_patterns: ClassVar[dict[str, list[str]]] = {}
