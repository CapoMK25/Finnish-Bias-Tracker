"""Scraper for Verkkouutiset (verkkouutiset slug).

National Coalition Party (Kokoomus) affiliated newspaper.
Bias classification: +1 (party-organ tier, right).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class VerkkouutisetScraper(RSSScraper):
    source_slug = "verkkouutiset"
    rss_url = "https://www.verkkouutiset.fi/feed/"
    language = "fi"
    min_request_interval_seconds: float = 5.0  # 12 req/min, very gentle
