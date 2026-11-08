"""Shared pacing for Mistral calls, so every call stays inside the workspace's allowance.

Mistral enforces limits per model: requests per minute and tokens per minute. Scoring,
embeddings and the scope gate used to sleep a fixed 1.2 s before each call, which is
far too fast for a model allowed 2 requests a minute, and a 429 was retried only 4 to
30 s later, inside the same rate-limit window. Now every call first asks acquire(), which
blocks until both budgets allow it, and a 429 blocks that model for a full window.

Allowances, as shown on the Mistral console's Limits page (November 2026), are built in.
Override or extend them with environment variables, all optional:

  MISTRAL_RPM_<MODEL>   requests per minute for one model, e.g. MISTRAL_RPM_CODESTRAL_2508=100
  MISTRAL_TPM_<MODEL>   tokens per minute for one model,   e.g. MISTRAL_TPM_CODESTRAL_2508=600000
  MISTRAL_RPM_DEFAULT / MISTRAL_TPM_DEFAULT   for models that are not built in

<MODEL> is the model name in capitals with every non-alphanumeric run turned into "_".
Raise them when the account's allowance is raised; a log line at the first call of each
model shows the numbers in use.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import deque
from collections.abc import Callable

import structlog

log = structlog.get_logger()

# Stay a little under the published number: Mistral counts in windows we cannot see.
SAFETY = 0.9
# After a 429, leave the model alone for a full minute window plus a margin.
PENALTY_SECONDS = 65.0
# Tokens are estimated, not counted. 3 characters per token over-estimates Finnish a little.
CHARS_PER_TOKEN = 3.0
# Typical size of a scoring answer, added to the prompt when budgeting tokens.
EXPECTED_OUTPUT_TOKENS = 600
# Only log a wait when it is long enough to matter.
LOG_WAITS_OVER_SECONDS = 2.0
# Waits shorter than this are rounding noise, not a reason to sleep and look again.
_EPSILON = 1e-6

# model -> (requests per minute, tokens per minute), from the console's Limits page.
_BUILTIN: dict[str, tuple[float, float]] = {
    "codestral-2508": (2, 40_000),
    "codestral-latest": (2, 40_000),
    "codestral-embed": (50, 50_000),
    "mistral-large-4": (50, 20_000),
}
_FALLBACK: tuple[float, float] = (30, 20_000)


def _number(value: str | None) -> float | None:
    """A positive number from an environment value, or None when it is missing or unusable."""
    if not value:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number > 0 else None


def limits_for(model: str) -> tuple[float, float]:
    """(requests per minute, tokens per minute) for a model."""
    key = re.sub(r"[^A-Za-z0-9]+", "_", model).upper()
    builtin = _BUILTIN.get(model)
    default_rpm = _number(os.environ.get("MISTRAL_RPM_DEFAULT")) or _FALLBACK[0]
    default_tpm = _number(os.environ.get("MISTRAL_TPM_DEFAULT")) or _FALLBACK[1]
    rpm = _number(os.environ.get(f"MISTRAL_RPM_{key}")) or (builtin[0] if builtin else default_rpm)
    tpm = _number(os.environ.get(f"MISTRAL_TPM_{key}")) or (builtin[1] if builtin else default_tpm)
    return rpm, tpm


def estimate_tokens(*texts: str) -> int:
    """A rough token count for the given texts (prompt side)."""
    return int(sum(len(t) for t in texts) / CHARS_PER_TOKEN) + 1


class RateLimiter:
    """Blocks callers until a model's request and token budgets allow another call."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_start: dict[str, float] = {}
        self._recent_tokens: dict[str, deque[tuple[float, int]]] = {}
        self._blocked_until: dict[str, float] = {}
        self._announced: set[str] = set()

    def _wait_needed(self, model: str, tokens: int) -> float:
        now = self._clock()
        rpm, tpm = limits_for(model)
        waits = [0.0]

        blocked = self._blocked_until.get(model, 0.0)
        if blocked > now:
            waits.append(blocked - now)

        last = self._last_start.get(model)
        if last is not None:
            interval = 60.0 / (rpm * SAFETY)
            if now - last < interval:
                waits.append(interval - (now - last))

        window = self._recent_tokens.get(model)
        if window:
            while window and now - window[0][0] >= 60.0:
                window.popleft()
            budget = tpm * SAFETY
            used = sum(t for _, t in window)
            # A single request bigger than the whole budget is let through when nothing else
            # is in flight, otherwise it would wait forever.
            if window and used + tokens > budget:
                need = used + tokens - budget
                freed = 0
                release_at = window[-1][0] + 60.0
                for stamp, spent in window:
                    freed += spent
                    if freed >= need:
                        release_at = stamp + 60.0
                        break
                waits.append(release_at - now)
        return max(waits)

    def acquire(self, model: str, tokens: int = 0) -> float:
        """Wait until the model may be called, record the call, return the seconds waited."""
        waited = 0.0
        while True:
            with self._lock:
                wait = self._wait_needed(model, tokens)
                if wait <= _EPSILON:
                    now = self._clock()
                    self._last_start[model] = now
                    self._recent_tokens.setdefault(model, deque()).append((now, tokens))
                    if model not in self._announced:
                        self._announced.add(model)
                        rpm, tpm = limits_for(model)
                        log.info("mistral_limiter_in_use", model=model, rpm=rpm, tpm=tpm)
                    return waited
            if waited == 0.0 and wait >= LOG_WAITS_OVER_SECONDS:
                log.info("mistral_waiting_for_allowance", model=model, wait_s=round(wait))
            self._sleep(wait)
            waited += wait

    def penalize(self, model: str, seconds: float = PENALTY_SECONDS) -> None:
        """Block a model for a while, used after Mistral answered 429."""
        with self._lock:
            self._blocked_until[model] = max(
                self._blocked_until.get(model, 0.0), self._clock() + seconds
            )


_default = RateLimiter()


def acquire(model: str, tokens: int = 0) -> float:
    return _default.acquire(model, tokens)


def penalize(model: str, seconds: float = PENALTY_SECONDS) -> None:
    _default.penalize(model, seconds)
