"""
Source-slug → scraper-class dispatch table.

When adding a new source:
1. Create the scraper class in src/scrapers/<slug>.py
2. Add the slug → class mapping here
3. Also seed the source in the DB (apps/api/src/db/seed.ts)

The dispatch table is intentionally explicit rather than dynamic import.
Eleven sources is small enough to enumerate, and explicit mapping is
grep-friendly when debugging "which scraper ran for what source?".
"""

from __future__ import annotations

from src.scrapers.demokraatti import DemokraattiScraper
from src.scrapers.hbl import HblScraper
from src.scrapers.hs import HsScraper
from src.scrapers.ilta_sanomat import IltaSanomatScraper
from src.scrapers.iltalehti import IltalehtiScraper
from src.scrapers.kansan_uutiset import KansanUutisetScraper
from src.scrapers.suomen_uutiset import SuomenUutisetScraper
from src.scrapers.suomenmaa import SuomenmaaScraper
from src.scrapers.svenska_yle import SvenskaYleScraper
from src.scrapers.verkkouutiset import VerkkouutisetScraper
from src.scrapers.yle import YleScraper

# Slug → scraper class. Slug matches the `slug` column in the sources
# table (and the source_slug field in BullMQ job payloads).
SCRAPERS = {
    "demokraatti": DemokraattiScraper,
    "helsingin-sanomat": HsScraper,
    "hufvudstadsbladet": HblScraper,
    "ilta-sanomat": IltaSanomatScraper,
    "iltalehti": IltalehtiScraper,
    "kansan-uutiset": KansanUutisetScraper,
    "suomen-uutiset": SuomenUutisetScraper,
    "suomenmaa": SuomenmaaScraper,
    "svenska-yle": SvenskaYleScraper,
    "verkkouutiset": VerkkouutisetScraper,
    "yle": YleScraper,
}
