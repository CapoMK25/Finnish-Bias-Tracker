#!/usr/bin/env bash
# check-ingestion.sh - one-screen health report for the scrape pipeline.
#
# On the server:
#   /opt/fbt/scripts/check-ingestion.sh            # last 4 hours
#   /opt/fbt/scripts/check-ingestion.sh 12         # last 12 hours
#
# Offline, on saved files (ps.txt worker_restarts.txt queue.json health.json
# api.log worker.log in one directory):
#   ./check-ingestion.sh --from-dir ./snapshot 6
#
# Exit code 0 = no problems found, 1 = at least one problem (see VERDICT).

set -u

API_URL="${API_URL:-http://localhost:3000}"
WORKER="${WORKER_CONTAINER:-fbt-scraper-worker-1}"
API_C="${API_CONTAINER:-fbt-api-1}"

if [ "${1:-}" = "--from-dir" ]; then
  DIR="${2:?usage: --from-dir DIR [hours]}"
  HOURS="${3:-4}"
else
  HOURS="${1:-4}"
  DIR="$(mktemp -d)"
  trap 'rm -rf "$DIR"' EXIT
  docker ps --format '{{.Names}}\t{{.Status}}' >"$DIR/ps.txt" 2>&1
  docker inspect -f '{{.RestartCount}}' "$WORKER" >"$DIR/worker_restarts.txt" 2>&1
  # no -f: a degraded API answers 503 with a useful JSON body we still want to read
  curl -s --max-time 10 "$API_URL/api/admin/queue/stats" >"$DIR/queue.json" 2>/dev/null
  curl -s --max-time 10 "$API_URL/api/admin/health" >"$DIR/health.json" 2>/dev/null
  docker logs --since "${HOURS}h" --timestamps "$API_C" >"$DIR/api.log" 2>&1
  docker logs --since "${HOURS}h" --timestamps "$WORKER" >"$DIR/worker.log" 2>&1
fi

python3 - "$DIR" "$HOURS" <<'PY'
import collections
import datetime as dt
import json
import re
import sys

d, hours = sys.argv[1], int(sys.argv[2])
now = dt.datetime.now(dt.timezone.utc)

# Sources that have a scraper in the Python worker (dispatch.py).
SCRAPED = [
    "yle", "helsingin-sanomat", "iltalehti", "ilta-sanomat", "demokraatti",
    "kansan-uutiset", "suomen-uutiset", "suomenmaa", "verkkouutiset",
    "hufvudstadsbladet", "svenska-yle",
]
EXPECTED_SERVICES = ["postgres", "redis", "api", "web", "reverse-proxy", "scraper-worker"]

problems, warnings = [], []


def read(name):
    try:
        with open(f"{d}/{name}", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def parse_ts(s):
    # docker --timestamps: 2026-10-26T17:03:32.123456789Z
    return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- containers
print(f"== containers ({now:%Y-%m-%d %H:%M} UTC) ==")
ps = [l for l in read("ps.txt").splitlines() if l.strip()]
for l in ps:
    print("  " + l.replace("\t", "  "))
running = {l.split("\t")[0] for l in ps}
for svc in EXPECTED_SERVICES:
    if not any(svc in n for n in running):
        problems.append(f"no running container for '{svc}'")
restarts = read("worker_restarts.txt").strip()
print(f"  worker restart count: {restarts or '?'}")
if restarts.isdigit() and int(restarts) > 3:
    warnings.append(f"worker has restarted {restarts} times (crash loop?)")

# --------------------------------------------------------------------- queue
print("\n== queue ==")
try:
    q = json.loads(read("queue.json"))
    counts, repeatables = q.get("counts", {}), q.get("repeatable_jobs", [])
    print(f"  counts: {counts}")
    print(f"  old repeatable schedules still registered: {len(repeatables)} (expected 0)")
    if repeatables:
        warnings.append("old BullMQ repeatable schedules still exist; remove them (removeAllRepeatableJobs)")
    if counts.get("waiting", 0) > 40:
        warnings.append(f"{counts['waiting']} jobs waiting: the worker is falling behind")
except (json.JSONDecodeError, TypeError):
    print("  (could not read /api/admin/queue/stats)")
    problems.append("queue stats endpoint unreachable")

# ------------------------------------------------------------ scheduler ticks
print(f"\n== scheduler ticks in the API log (last {hours}h) ==")
ticks = []
for l in read("api.log").splitlines():
    m = re.search(r"hourly_scrapes_enqueued\s+(\{.*\})", l)
    if m:
        try:
            info = json.loads(m.group(1))
            ticks.append((parse_ts(l), info))
        except (json.JSONDecodeError, ValueError):
            pass
for ts, info in ticks[-8:]:
    print(f"  {ts:%m-%d %H:%M}  slot={info.get('slot')}  newly queued={info.get('created')}/{info.get('sources')}")
if not ticks:
    problems.append(f"no hourly_scrapes_enqueued in the API log for {hours}h: scheduler is not running")
else:
    age = (now - ticks[-1][0]).total_seconds() / 60
    if age > 75:
        problems.append(f"last scheduler tick was {age:.0f} min ago (should be <= 60)")

# -------------------------------------------------------------- jobs per hour
print(f"\n== worker jobs per hour, UTC (last {hours}h) ==")
EV = re.compile(
    r"^(\d{4}-\d\d-\d\dT\d\d):\d\d:\d\d\S*\s.*?\b"
    r"(worker_job_received|worker_job_completed|worker_job_failed|worker_job_timeout)\b"
    r".*?\bsource_slug=([\w-]+)"
)
by_hour = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for l in read("worker.log").splitlines():
    m = EV.search(l)
    if m:
        by_hour[m.group(1)][m.group(3)][m.group(2)] += 1

current_hour = now.strftime("%Y-%m-%dT%H")
print(f"  {'hour':<14}{'sources':>8}{'received':>10}{'completed':>11}{'failed':>8}   notes")
for hour in sorted(by_hour):
    srcs = by_hour[hour]
    recv = sum(c["worker_job_received"] for c in srcs.values())
    done = sum(c["worker_job_completed"] for c in srcs.values())
    fail = sum(c["worker_job_failed"] + c["worker_job_timeout"] for c in srcs.values())
    loops = {
        s: c["worker_job_received"]
        for s, c in srcs.items()
        if c["worker_job_received"] > 1 and c["worker_job_failed"] + c["worker_job_timeout"] == 0
    }
    note = ""
    if loops:
        note = "LOOP? " + ", ".join(f"{s} x{n}" for s, n in sorted(loops.items()))
        problems.append(
            f"{hour}: same source received more than once without a failure ({note}). "
            "A manual run in the same hour also looks like this."
        )
    print(f"  {hour:<14}{len(srcs):>8}{recv:>10}{done:>11}{fail:>8}   {note}")

complete = [h for h in sorted(by_hour) if h < current_hour]
if complete:
    last = complete[-1]
    missing = [s for s in SCRAPED if by_hour[last][s]["worker_job_received"] == 0]
    if missing:
        problems.append(f"{last}: no job ran for {', '.join(missing)}")
elif not by_hour:
    problems.append(f"no worker_job_received lines in the last {hours}h: nothing is running")

# ------------------------------------------------------------------ freshness
print("\n== source freshness (from /api/admin/health) ==")
try:
    h = json.loads(read("health.json"))
    src = {s["slug"]: s for s in h.get("sources", [])}
    print(f"  api status: {h.get('status')}")
    sch = h.get("scheduler")
    if sch:
        print(
            f"  scheduler: running={sch.get('running')} healthy={sch.get('healthy')} "
            f"last_success={sch.get('last_success_at')} next_tick={sch.get('next_tick_at')}"
        )
        if not sch.get("healthy"):
            problems.append("API reports the hourly scheduler is not healthy")
        if sch.get("last_error"):
            warnings.append(f"scheduler last error: {sch['last_error']}")
    for slug in SCRAPED:
        s = src.get(slug)
        if not s:
            print(f"  {slug:<20} (not in health output)")
            continue
        print(f"  {slug:<20} {s.get('freshness'):<9} {s.get('minutes_since_last_score')} min since last score")
        if s.get("freshness") in ("critical", "never"):
            problems.append(f"{slug} is {s.get('freshness')}")
        elif s.get("freshness") == "stale":
            warnings.append(f"{slug} is stale (2-6 h)")
except (json.JSONDecodeError, TypeError):
    print("  (could not read /api/admin/health)")
    problems.append("health endpoint unreachable")

# -------------------------------------------------------------------- verdict
print("\n== VERDICT ==")
for w in warnings:
    print(f"  warning: {w}")
for p in problems:
    print(f"  PROBLEM: {p}")
if not problems:
    print("  OK: no problems found" + (" (see warnings above)" if warnings else ""))
sys.exit(1 if problems else 0)
PY
