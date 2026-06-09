"""Per-domain HTTP rate limiting for scrapers.

Maintains a module-level dict mapping domain -> last_request_time.
Each fetch is gated by min_interval_seconds since the previous fetch
to the same domain.

Per-process state. Two worker processes would each have their own
limiter; the effective rate would be 2x the intended limit. For
single-worker deployments this is fine.

For multi-worker production, replace this with a Redis ZSET-backed
sliding window.
"""

from __future__ import annotations

import time
from threading import Lock
from urllib.parse import urlparse

import structlog

log = structlog.get_logger()

_last_request_time: dict[str, float] = {}
_lock = Lock()


def throttle_for_domain(url: str, min_interval_seconds: float) -> None:
    """Block until min_interval_seconds has passed since the last request to this domain.

    Safe for concurrent use within a single process via threading.Lock.
    """
    domain = urlparse(url).netloc
    if not domain:
        log.warning("rate_limit_no_domain", url=url)
        return

    with _lock:
        now = time.monotonic()
        last = _last_request_time.get(domain, 0.0)
        elapsed = now - last

        if elapsed < min_interval_seconds:
            sleep_for = min_interval_seconds - elapsed
            log.debug(
                "rate_limit_throttle",
                domain=domain,
                sleep_seconds=round(sleep_for, 2),
                interval=min_interval_seconds,
            )
            time.sleep(sleep_for)
            now = time.monotonic()

        _last_request_time[domain] = now
