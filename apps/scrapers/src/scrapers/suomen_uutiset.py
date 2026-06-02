"""Scraper for Suomen Uutiset (suomen-uutiset slug).

Finns Party (Perussuomalaiset) affiliated newspaper.
Bias classification: +2 (party-organ tier, right).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class SuomenUutisetScraper(RSSScraper):
    source_slug = "suomen-uutiset"
    rss_url = "https://www.suomenuutiset.fi/feed/"
    language = "fi"
