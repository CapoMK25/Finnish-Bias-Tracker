"""Scraper for Hufvudstadsbladet (hufvudstadsbladet slug).

Swedish-language Finnish daily, owned by KSF Media, often editorially
aligned with the Swedish People's Party (RKP).
Bias classification: -1 (center-liberal, mainstream).
Language: Swedish (sv).
"""

from __future__ import annotations

from typing import ClassVar

from src.scrapers.base import RSSScraper


class HblScraper(RSSScraper):
    source_slug = "hufvudstadsbladet"
    rss_url = "https://www.hbl.fi/feed/"
    language = "sv"
    article_type_patterns: ClassVar[dict[str, list[str]]] = {
        "opinion": ["/ledare/", "/opinion/", "/debatt/", "/kolumn/"],
        "analysis": ["/analys/"],
    }
