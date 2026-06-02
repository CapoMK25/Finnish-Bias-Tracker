"""Scraper for Ilta-Sanomat (ilta-sanomat slug).

Sanoma Group tabloid. Bias classification: +1 (center-right tabloid).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class IltaSanomatScraper(RSSScraper):
    source_slug = "ilta-sanomat"
    rss_url = "https://www.is.fi/rss/tuoreimmat.xml"
    language = "fi"
