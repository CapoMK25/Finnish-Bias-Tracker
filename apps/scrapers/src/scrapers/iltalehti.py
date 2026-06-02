"""Scraper for Iltalehti (iltalehti slug).

Alma Media tabloid. Bias classification: +1 (center-right populist).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class IltalehtiScraper(RSSScraper):
    source_slug = "iltalehti"
    rss_url = "https://www.iltalehti.fi/rss/uutiset.xml"
    language = "fi"
