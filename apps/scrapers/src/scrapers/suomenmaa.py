"""Scraper for Suomenmaa (suomenmaa slug).

Centre Party (Keskusta) affiliated newspaper. Requires www. prefix on URL.
Bias classification: 0 (party-organ tier, party-of-the-center).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class SuomenmaaScraper(RSSScraper):
    source_slug = "suomenmaa"
    rss_url = "https://www.suomenmaa.fi/feed/"
    language = "fi"
