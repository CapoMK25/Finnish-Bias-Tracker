"""LLM scope gate: one cheap, batched call per feed for what word lists cannot see.

Rules (src/relevance.py) catch sports sections, foreign countries and so on.
They cannot recognise a lifestyle or human-interest piece in a domestic section
("candy rounds", "Lucia candidates", "fashion trends"). This gate asks a small
model, once per feed and only for entries that are new and passed the rules,
whether each item is about Finnish politics or public affairs.

Safety properties, because a wrong DROP silently removes coverage:
  - Off unless SCOPE_GATE=on (set it in .env after running scripts/eval_scope_gate.py).
  - Conservative prompt: "if unsure, KEEP".
  - Fails open: any error, malformed answer or missing verdict keeps the entry.
  - Every drop is logged with the model's reason so it can be audited.
  - Verdicts are cached per URL, so a long-lived worker never re-asks about an entry.

Environment:
  SCOPE_GATE        on | off (default off)
  SCOPE_GATE_MODEL  default codestral-2508, the chat model this project's Mistral key can
                    use. mistral-small-latest and mistral-medium-latest answered 429 with a
                    limit of 0 requests per minute on that key, so they are not the default.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Sequence

import structlog

log = structlog.get_logger()

DEFAULT_MODEL = "codestral-2508"
BATCH_SIZE = 40
SUMMARY_CHARS = 160
_REQUEST_TIMEOUT_MS = 60_000
_CACHE_MAX = 5000
_MIN_SECONDS_BETWEEN_CALLS = 1.2  # Mistral free tier allows about one request per second

# url -> (keep, reason). Only explicit verdicts are cached, never failures.
_cache: dict[str, tuple[bool, str]] = {}
_last_call = 0.0
_client_instance: object | None = None

SYSTEM_PROMPT = """\
You are a strict relevance filter for a research project that analyses political \
framing in the FINNISH press. The project covers Finnish politics only.

For every numbered news item decide whether it belongs in the project.

KEEP when the item is about Finnish politics or public affairs: the government, \
parliament and parties, elections, legislation, public finances and tax policy, \
welfare, health and education policy, immigration and integration policy, Finnish \
security, defence and foreign policy (including Finland's role in NATO and the EU), \
politicians and public officials, and opinion columns about these topics. Also KEEP \
media, culture-war and identity debates when they are about Finnish society and politics.

DROP only when the item is clearly outside that scope:
- sports, entertainment, celebrities, music, film, TV, books and arts reviews
- lifestyle: fashion, beauty, food, travel, home, pets, horoscopes, consumer tips
- everyday human-interest and local colour with no public-policy angle \
(traditions, anecdotes, personal stories)
- crime, accidents, weather and health news with no policy angle
- business, company and market news
- news about other countries and international affairs with no Finnish angle

If you are unsure, KEEP. Never drop an item only because it is short, emotional or unusual.

Answer with JSON only, one entry per item, in order:
{"results": [{"id": 1, "keep": true, "why": "finnish politics"}, \
{"id": 2, "keep": false, "why": "sports"}]}
"why" is at most four words."""


def enabled() -> bool:
    return os.environ.get("SCOPE_GATE", "").strip().lower() in {"1", "true", "on", "yes"}


def _model() -> str:
    return os.environ.get("SCOPE_GATE_MODEL", "").strip() or DEFAULT_MODEL


def _content_to_text(content: object) -> str:
    """Mistral returns either a string or a list of content chunks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for chunk in content:
            text = chunk if isinstance(chunk, str) else getattr(chunk, "text", "")
            parts.append(text or "")
        return "".join(parts)
    return ""


def _client() -> object:
    global _client_instance
    if _client_instance is None:
        from src.config import settings  # lazy: importing this module needs no .env

        try:
            from mistralai.client import Mistral
        except ImportError:  # older SDK layout
            from mistralai import Mistral
        if not settings.mistral_api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set")
        _client_instance = Mistral(api_key=settings.mistral_api_key, timeout_ms=_REQUEST_TIMEOUT_MS)
    return _client_instance


def _complete(system: str, user: str, max_tokens: int) -> str:
    """One chat call. Isolated so tests can replace it."""
    global _last_call
    wait = _MIN_SECONDS_BETWEEN_CALLS - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()
    client = _client()
    response = client.chat.complete(  # type: ignore[attr-defined]
        model=_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    if not response.choices:
        return ""
    return _content_to_text(response.choices[0].message.content)


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _as_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "keep", "yes"}:
            return True
        if v in {"false", "drop", "no"}:
            return False
    return None


def _parse(raw: str, count: int) -> dict[int, tuple[bool, str]]:
    """Map 1-based item id -> (keep, why). Anything unreadable is simply absent."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return {}
    parsed: dict[int, tuple[bool, str]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        idx, keep = item.get("id"), _as_bool(item.get("keep"))
        if isinstance(idx, int) and 1 <= idx <= count and keep is not None:
            parsed[idx] = (keep, str(item.get("why") or "")[:40])
    return parsed


def _classify_chunk(chunk: Sequence[tuple[str, str, str]]) -> dict[str, tuple[bool, str]]:
    lines = []
    for i, (_, title, summary) in enumerate(chunk, start=1):
        brief = _plain(summary)[:SUMMARY_CHARS]
        lines.append(f"{i}. {_plain(title)}" + (f" | {brief}" if brief else ""))
    user = "Items:\n" + "\n".join(lines)

    try:
        raw = _complete(SYSTEM_PROMPT, user, max_tokens=80 + 30 * len(chunk))
    except Exception as e:
        log.warning("scope_gate_failed_keeping_all", error=str(e), items=len(chunk))
        return {key: (True, "gate-error") for key, _, _ in chunk}

    parsed = _parse(raw, len(chunk))
    if not parsed:
        log.warning("scope_gate_unreadable_answer_keeping_all", items=len(chunk), raw=raw[:120])
        return {key: (True, "gate-unreadable") for key, _, _ in chunk}

    verdicts: dict[str, tuple[bool, str]] = {}
    for i, (key, _, _) in enumerate(chunk, start=1):
        if i in parsed:
            verdicts[key] = parsed[i]
            if len(_cache) >= _CACHE_MAX:
                _cache.clear()
            _cache[key] = parsed[i]
        else:
            verdicts[key] = (True, "no-verdict")  # not cached: ask again next time
    return verdicts


def classify(items: Sequence[tuple[str, str, str]]) -> dict[str, tuple[bool, str]]:
    """items: (key, title, summary) where key is the URL. Returns key -> (keep, why)."""
    verdicts: dict[str, tuple[bool, str]] = {}
    todo: list[tuple[str, str, str]] = []
    for item in items:
        if item[0] in _cache:
            verdicts[item[0]] = _cache[item[0]]
        else:
            todo.append(item)
    for start in range(0, len(todo), BATCH_SIZE):
        verdicts.update(_classify_chunk(todo[start : start + BATCH_SIZE]))
    return verdicts
