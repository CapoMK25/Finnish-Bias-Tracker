"""Scraper for Suomenmaa (suomenmaa slug).

Centre Party (Keskusta) affiliated newspaper. Requires www. prefix on URL.
Bias classification: 0 (party-organ tier, party-of-the-center).
"""

from __future__ import annotations

from typing import Any
from curl_cffi import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.scrapers.rate_limit import throttle_for_domain
from .base import RSSScraper


class SuomenmaaScraper(RSSScraper):
    source_slug = "suomenmaa"
    rss_url = "https://www.suomenmaa.fi/feed/"
    language = "fi"
    min_request_interval_seconds: float = 5.0  # 12 req/min, very gentle

    def _fetch_url_sync(self, url: str) -> str:
        """
        Synchronous impersonation block used to safely pull content 
        without getting tripped up by the async loop teardown.
        """
        response = requests.get(
            url, 
            impersonate="chrome110", 
            timeout=15
        )
        response.raise_for_status()
        return response.text

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_article_html(self, url: str) -> str:
        """
        Override the base class fetcher.
        Bypass Cloudflare using curl_cffi instead of the default httpx client.
        """
        throttle_for_domain(url, self.min_request_interval_seconds)
        self.log.info("fetching_html_curl_cffi", url=url)
        return self._fetch_url_sync(url)