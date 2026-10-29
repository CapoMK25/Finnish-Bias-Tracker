"""
Job processor — bridges BullMQ jobs to the existing scrape orchestration.

When BullMQ delivers a job, this function:
1. Extracts the source_slug and limit from the payload
2. Looks up the scraper class via dispatch
3. Runs the scrape (in a worker thread) using run_for_source
4. Returns a summary dict that BullMQ stores on the completed job

Exceptions propagate to BullMQ, which handles retries based on the
queue's configured retry policy.

Why the scrape runs in a thread: it is synchronous and takes ~1 minute. Run
directly inside this coroutine it would block the event loop, so the worker
could not renew the job's 30-second lock. The job would then be treated as
stalled and silently run again (and again). In a thread, lock renewal keeps
working and each job runs exactly once.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from src.config import settings
from src.run import run_for_source
from src.worker.dispatch import SCRAPERS

log = structlog.get_logger()

# Hard ceiling for one scrape. A normal run takes about a minute; the longest
# legitimate case is Mistral rate-limit pauses (~40 s per article x 10). Past
# this we give up, so one hung network call cannot block the single worker
# (and with it every later source) forever.
SCRAPE_TIMEOUT_S = 20 * 60


def _holla_heartbeat() -> None:
    """Tell the dead-man's-switch monitor that a job just succeeded.

    No-op when HEALTHCHECK_PING_URL is not set. Never raises: a monitoring
    hiccup must not turn a successful scrape into a failed job.
    """
    try:
        # getattr: stays as is even if config.py has no such field yet
        url = getattr(settings, "healthcheck_ping_url", "")
        if url:
            httpx.get(url, timeout=5.0)
    except Exception as exc:
        log.warning("heartbeat_ping_failed", error=repr(exc))


async def process_scrape_job(job: Any, _token: str | None = None) -> dict[str, Any]:
    """
    BullMQ job processor.

    Args:
        job: BullMQ Job object. The payload is on job.data.
        _token: Internal BullMQ token. Unused but required by the worker protocol.

    Returns:
        A summary dict that BullMQ stores on the completed job.

    Raises:
        Any exception from the scrape. BullMQ retries based on the
        queue's configured retry policy.
    """
    data = job.data
    source_slug = data.get("source_slug")
    limit = data.get("limit", 30)
    job_id = str(job.id)

    if not source_slug:
        raise ValueError(f"Job {job_id} missing source_slug")

    if source_slug not in SCRAPERS:
        log.error("worker_job_unknown_source", job_id=job_id, source_slug=source_slug)
        raise ValueError(
            f"Job {job_id} references unknown source: {source_slug}. "
            f"Known sources: {sorted(SCRAPERS.keys())}"
        )

    log.info(
        "worker_job_received",
        job_id=job_id,
        source_slug=source_slug,
        limit=limit,
    )

    start = time.monotonic()

    # Only the scrape itself is inside the try block. A scrape that succeeded
    # must never be reported as failed (and retried) because of bookkeeping
    # or logging that happens afterwards.
    try:
        summary = await asyncio.wait_for(
            asyncio.to_thread(run_for_source, slug=source_slug, limit=limit),
            timeout=SCRAPE_TIMEOUT_S,
        )
    except TimeoutError:
        log.error(
            "worker_job_timeout",
            job_id=job_id,
            source_slug=source_slug,
            timeout_s=SCRAPE_TIMEOUT_S,
        )
        raise
    except Exception as exc:
        log.error(
            "worker_job_failed",
            job_id=job_id,
            source_slug=source_slug,
            elapsed_s=round(time.monotonic() - start, 2),
            error=repr(exc),
            error_type=type(exc).__name__,
        )
        raise  # Let BullMQ handle retry

    elapsed_s = round(time.monotonic() - start, 2)

    if not isinstance(summary, dict):
        # run_for_source is documented to return a stats dict. Fail loudly
        # with a readable message instead of a confusing TypeError later.
        raise TypeError(
            f"run_for_source returned {type(summary).__name__}, expected dict: {summary!r}"
        )

    # Pass the stats as a single field instead of splatting them into the
    # logger call, so the shape of the stats can never break logging.
    log.info(
        "worker_job_completed",
        job_id=job_id,
        source_slug=source_slug,
        elapsed_s=elapsed_s,
        stats=summary,
    )

    await asyncio.to_thread(_holla_heartbeat)

    return {
        "source_slug": source_slug,
        "elapsed_s": elapsed_s,
        **summary,
    }