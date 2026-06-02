"""Scraper for Kansan Uutiset (kansan-uutiset slug).

Left Alliance (Vasemmistoliitto) party organ. KU has migrated from
kansanuutiset.fi to ku.fi; canonical feed is at ku.fi/feed.
Bias classification: -2 (party-organ tier, left).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class KansanUutisetScraper(RSSScraper):
    source_slug = "kansan-uutiset"
    rss_url = "https://www.ku.fi/feed"
    language = "fi"
