#!/usr/bin/env bash
#
# Scrape only Verkkouutiset, for isolated testing (e.g. reproducing
# scoring issues like #249 without burning rate-limit budget on the
# other 10 sources).
#
# Usage:
#   ./scripts/scrape_verkkouutiset.sh          # default 20 articles
#   ./scripts/scrape_verkkouutiset.sh 10       # 10 articles
#
# Behavior:
#   - Exits 75 cleanly if Python reports LLM quota exhausted.
#   - Exits with the same code as Python on any other failure.
#
set -euo pipefail

# Resolve to the scrapers workspace root so `python -m src.run` finds the package
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$SCRIPT_DIR")"

LIMIT="${1:-20}"
EX_TEMPFAIL=75   # Unix sysexits.h — temporary failure (LLM quota exhausted)
SOURCE="verkkouutiset"

echo "================================================================"
echo "Scraping ${SOURCE}, limit=${LIMIT}"
echo "================================================================"

set +e
python -m src.run --source "${SOURCE}" --limit "${LIMIT}"
exit_code=$?
set -e

case "${exit_code}" in
    0)
        echo ""
        echo "================================================================"
        echo "  ${SOURCE} completed."
        echo "================================================================"
        ;;
    ${EX_TEMPFAIL})
        echo ""
        echo "================================================================"
        echo "  LLM quota exhausted for today. Stopped."
        echo "  Retry tomorrow (resets ~10:00 Helsinki / 00:00 PT)"
        echo "================================================================"
        ;;
    *)
        echo ""
        echo "================================================================"
        echo "  ${SOURCE} exited with code ${exit_code} — stopping."
        echo "================================================================"
        exit "${exit_code}"
        ;;
esac