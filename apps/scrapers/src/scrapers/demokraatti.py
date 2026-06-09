"""Scraper for Demokraatti (demokraatti slug).

SDP-affiliated newspaper. Bias classification: -2 (party-organ tier, left).
"""

from __future__ import annotations

from src.scrapers.base import RSSScraper


class DemokraattiScraper(RSSScraper):
    source_slug = "demokraatti"
    rss_url = "https://demokraatti.fi/feed/"
    language = "fi"
    min_request_interval_seconds: float = 5.0  # 12 req/min, very gentle
