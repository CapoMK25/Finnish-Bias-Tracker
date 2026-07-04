"""PostgreSQL connection management for the Python scraper.

Uses psycopg's connection pool to avoid opening a new TCP connection per article.
"""

from __future__ import annotations

import structlog
import atexit
from psycopg_pool import ConnectionPool

from src.config import settings

log = structlog.get_logger()

# Module-level pool. Initialized lazily on first use.
_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Return the shared connection pool, initializing it on first call."""
    global _pool
    if _pool is None:
        log.info("initializing_db_pool", url_host=_sanitize_url(settings.database_url))
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=4,
            timeout=10.0,
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Close the pool. Useful for clean shutdown in tests or scripts."""
    global _pool
    if _pool is not None:
        log.info("closing_db_pool")
        _pool.close()
        _pool = None    
        
    atexit.register(close_pool)


def _sanitize_url(url: str) -> str:
    """Strip password from URL for safe logging."""
    if "@" not in url:
        return url
    scheme_user, _, host_part = url.partition("@")
    if ":" in scheme_user:
        scheme_user = scheme_user.rsplit(":", 1)[0]
    return f"{scheme_user}@{host_part}"
