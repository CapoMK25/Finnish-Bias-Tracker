#!/usr/bin/env bash
# Run the BullMQ worker.
#
# Usage:
#   ./scripts/worker.sh           # run in foreground
#   nohup ./scripts/worker.sh &   # run in background (no logs to stdout)
#
# Stops gracefully on Ctrl+C (SIGINT) or SIGTERM. Finishes current job
# before exiting.

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Error: Python virtual environment not found. Run: python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate

exec python -m src.worker.main
