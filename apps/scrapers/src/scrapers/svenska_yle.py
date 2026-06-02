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
from URL structure; article_type_patterns is empty.
"""

from __future__ import annotations

from typing import ClassVar

from src.scrapers.base import RSSScraper


class SvenskaYleScraper(RSSScraper):
    source_slug = "svenska-yle"
    rss_url = "https://svenska.yle.fi/rss/senaste-nytt"
    language = "sv"
    article_type_patterns: ClassVar[dict[str, list[str]]] = {}
