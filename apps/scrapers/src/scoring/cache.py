"""LLM response caching to avoid re-spending API quota during development.

Caches by content hash, so identical (model, prompt_version, title, body)
inputs return the cached score without an API call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import structlog

from src.scoring.base import BiasScore

log = structlog.get_logger()

CACHE_DIR = Path.home() / ".cache" / "finnish-bias-tracker" / "scores"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(*, model: str, prompt_version: str, title: str, body: str) -> str:
    """Stable cache key from article content + model + prompt version."""
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(prompt_version.encode())
    h.update(title.encode())
    h.update(body.encode())
    return h.hexdigest()


def load_cached(key: str) -> BiasScore | None:
    """Return cached BiasScore if present, else None."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return BiasScore(**data)
    except (json.JSONDecodeError, TypeError) as e:
        log.warning("cache_load_failed", key=key, error=str(e))
        return None


def save_cached(key: str, score: BiasScore) -> None:
    """Persist a BiasScore to the cache."""
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(asdict(score), indent=2))
