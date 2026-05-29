#!/usr/bin/env bash
# Scrape all currently-implemented sources in a sequence.
# Run from apps/scrapers/ with venv active.

set -e

SOURCES=("yle" "helsingin-sanomat" "iltalehti" "ilta-sanomat")
LIMIT="${1:-20}"

for source in "${SOURCES[@]}"; do
    echo ""
    echo "================================================================"
    echo "Scraping: $source (limit $LIMIT)"
    echo "================================================================"
    python -m src.run --source "$source" --limit "$LIMIT"
done

echo ""
echo "All sources scraped!"
