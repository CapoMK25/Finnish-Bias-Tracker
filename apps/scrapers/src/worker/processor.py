"""
Job processor — bridges BullMQ jobs to the existing scrape orchestration.

When BullMQ delivers a job, this function:
1. Extracts the source_slug and limit from the payload
2. Looks up the scraper class via dispatch
3. Runs the scrape using the existing run_for_source orchestration
4. Returns a summary dict that BullMQ stores on the completed job

Exceptions propagate to BullMQ, which handles retries based on the
queue's configured retry policy (3 attempts, exponential backoff).
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from src.run import run_for_source
from src.worker.dispatch import SCRAPERS

log = structlog.get_logger()


async def process_scrape_job(job: Any, _token: str | None = None) -> dict[str, Any]:
    """
    BullMQ job processor.

    Args:
        job: BullMQ Job object. The payload is on job.data.
        _token: Internal BullMQ token. Unused but required by the worker protocol.

    Returns:
        A summary dict that BullMQ stores on the completed job. Visible
        in the queue stats endpoint.

    Raises:
        Any exception from the scrape. BullMQ retries based on the
        queue's configured retry policy.
    """
    data = job.data
    source_slug = data.get("source_slug")
    limit = data.get("limit", 30)
    job_id = job.id

    if not source_slug:
        raise ValueError(f"Job {job_id} missing source_slug")

    if source_slug not in SCRAPERS:
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

    try:
        # Delegate to the existing run orchestration. Returns a stats dict
        # with scraped/new/duplicate/scored/skipped/failed counts.
        summary = run_for_source(slug=source_slug, limit=limit)

        elapsed_s = time.monotonic() - start

        log.info(
            "worker_job_completed",
            job_id=job_id,
            source_slug=source_slug,
            elapsed_s=round(elapsed_s, 2),
            **summary,
        )

        return {
            "source_slug": source_slug,
            "elapsed_s": round(elapsed_s, 2),
            **summary,
        }

    except Exception as exc:
        elapsed_s = time.monotonic() - start
        log.error(
            "worker_job_failed",
            job_id=job_id,
            source_slug=source_slug,
            elapsed_s=round(elapsed_s, 2),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise  # Let BullMQ handle retry
