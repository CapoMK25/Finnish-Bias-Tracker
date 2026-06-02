"""Scraper for Helsingin Sanomat (helsingin-sanomat slug).

Finland's "newspaper of record". Sanoma Group ownership.
Bias classification: -1 (center-left mainstream).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class HsScraper(RSSScraper):
    source_slug = "helsingin-sanomat"
    rss_url = "https://www.hs.fi/rss/tuoreimmat.xml"
    language = "fi"
