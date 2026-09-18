#!/usr/bin/env bash
#
# Audit script to verify BullMQ cron and job state inside the production Redis container.
# Follows the MAOC engineering approach for validation.

set -euo pipefail

echo "================================================================="
echo "Inspecting BullMQ 'scrape-jobs' Queue inside Production Redis..."
echo "================================================================="

# Execute keys query against the designated compose service name
KEYS=$(docker compose -f docker-compose.prod.yml exec -T redis redis-cli keys "bull:scrape-jobs:*")

if echo "$KEYS" | grep -q "repeat"; then
    echo -e "\nSUCCESS: Found repeatable job keys! Hono has automated the queue."
    echo "-----------------------------------------------------------------"
    echo "$KEYS" | grep "repeat"
else
    echo -e "\nWARNING: No repeatable keys found. Check your Hono api startup logs."
fi

echo -e "\nFull 'scrape-jobs' Cache Topology:"
echo "-----------------------------------------------------------------"
echo "$KEYS"
echo "================================================================="
