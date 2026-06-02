#!/usr/bin/env bash
#
# Scrape all currently-implemented sources sequentially.
#
# Usage:
#   ./scripts/scrape_all.sh          # default 20 articles per source
#   ./scripts/scrape_all.sh 10       # 10 articles per source
#
# Behavior:
#   - Stops cleanly if Python exits with code 75 (LLM quota exhausted).
#   - Stops on any other non-zero exit (real errors).
#   - Reports which sources completed and which were skipped.
#
set -euo pipefail

# Resolve to the scrapers workspace root so `python -m src.run` finds the package
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

LIMIT="${1:-20}"
EX_TEMPFAIL=75   # Unix sysexits.h — temporary failure (LLM quota exhausted)

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

completed=()
last_source=""

echo "================================================================"
echo "Scraping ${#SOURCES[@]} sources, limit=${LIMIT} per source"
echo "================================================================"

for source in "${SOURCES[@]}"; do
    last_source="${source}"
    echo ""
    echo "---- ${source} ----"

    # Don't let set -e bail us out before we inspect the exit code
    set +e
    python -m src.run --source "${source}" --limit "${LIMIT}"
    exit_code=$?
    set -e

    case "${exit_code}" in
        0)
            completed+=("${source}")
            ;;
        ${EX_TEMPFAIL})
            echo ""
            echo "================================================================"
            echo "  LLM quota exhausted for today. Stopping after: ${source}"
            echo "  Retry tomorrow (resets ~10:00 Helsinki / 00:00 PT)"
            echo "================================================================"
            break
            ;;
        *)
            echo ""
            echo "================================================================"
            echo "  ${source} exited with code ${exit_code} — stopping."
            echo "================================================================"
            exit "${exit_code}"
            ;;
    esac
done

# Compute skipped sources (anything after last_source that wasn't reached)
skipped=()
seen_last=false
for source in "${SOURCES[@]}"; do
    if [ "${seen_last}" = "true" ]; then
        skipped+=("${source}")
    fi
    if [ "${source}" = "${last_source}" ]; then
        seen_last=true
    fi
done

echo ""
echo "================================================================"
echo "Summary"
echo "================================================================"
echo "Completed (${#completed[@]}): ${completed[*]:-none}"
if [ "${#skipped[@]}" -gt 0 ]; then
    echo "Skipped (${#skipped[@]}):   ${skipped[*]}"
fi
echo "================================================================"
