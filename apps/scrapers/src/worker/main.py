"""
Worker entry point.

Long-running process. Connects to the same Redis instance as the API,
consumes jobs from the 'scrape-jobs' queue, and runs the corresponding
scraper for each job.

Run with:
    python -m src.worker.main

Or via the dedicated script (see scripts/worker.sh).

Graceful shutdown on SIGINT/SIGTERM. Worker finishes the current job
before exiting (BullMQ's stalled-job-detection re-queues if it doesn't).
"""

from __future__ import annotations

import asyncio
import signal
import sys

import structlog
from bullmq import Worker
from dotenv import load_dotenv

from src.config import settings
from src.worker.processor import process_scrape_job

load_dotenv()

log = structlog.get_logger()

QUEUE_NAME = "scrape-jobs"


async def run_worker() -> None:
    """
    Start the worker and block until a shutdown signal is received.
    """
    redis_url = settings.redis_url

    log.info(
        "worker_starting",
        queue=QUEUE_NAME,
        redis_url=redis_url.split("@")[-1] if "@" in redis_url else redis_url,
        concurrency=1,
    )

    worker = Worker(
        QUEUE_NAME,
        process_scrape_job,
        {
            "connection": redis_url,
            "concurrency": 1,
            # Don't auto-run; we manage the lifecycle explicitly below.
        },
    )

    # Wire up graceful shutdown.
    shutdown_event = asyncio.Event()

    def handle_shutdown(signum: int, _frame) -> None:
        log.info("worker_shutdown_signal_received", signum=signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    log.info("worker_ready")

    # Block until shutdown signal.
    await shutdown_event.wait()

    log.info("worker_closing")
    await worker.close()
    log.info("worker_closed")


def main() -> None:
    """CLI entry point."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        log.info("worker_interrupted")
        sys.exit(0)


if __name__ == "__main__":
    main()
