#!/usr/bin/env bash
# Scrape all currently-implemented sources in a sequence.
# Run from apps/scrapers/ with venv active.

set -e

LIMIT="${1:-20}"

SOURCES=(
    "yle"
    "helsingin-sanomat"
    "iltalehti"
    "ilta-sanomat"
    "kansan-uutiset"
    "demokraatti"
    "verkkouutiset"
    "suomen-uutiset"
    "suomenmaa"
    "hufvudstadsbladet"
    "svenska-yle"
)

for source in "${SOURCES[@]}"; do
    echo ""
    echo "================================================================"
    echo "Scraping: $source (limit $LIMIT)"
    echo "================================================================"
    python -m src.run --source "$source" --limit "$LIMIT"
done

echo ""
echo "All sources scraped!"
