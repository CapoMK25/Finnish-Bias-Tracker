"""Tests for the LLM scope gate. The model call is replaced, so no API key or network is needed.

Run: cd apps/scrapers && pytest tests/test_scope_gate.py -q
"""

import json

import pytest

from src import scope_gate


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    scope_gate._cache.clear()
    monkeypatch.delenv("SCOPE_GATE", raising=False)
    monkeypatch.delenv("SCOPE_GATE_MODEL", raising=False)
    yield
    scope_gate._cache.clear()


def fake_model(monkeypatch, answer_for):
    """answer_for(titles: list[str]) -> JSON string. Records every call."""
    calls = []

    def _complete(system, user, max_tokens):
        titles = [line.split(". ", 1)[1].split(" | ")[0] for line in user.splitlines()[1:]]
        calls.append({"system": system, "user": user, "titles": titles, "max_tokens": max_tokens})
        return answer_for(titles)

    monkeypatch.setattr(scope_gate, "_complete", _complete)
    return calls


def verdict_json(drop_words):
    def build(titles):
        results = [
            {"id": i, "keep": not any(w in t for w in drop_words), "why": "test"}
            for i, t in enumerate(titles, start=1)
        ]
        return json.dumps({"results": results})

    return build


ITEMS = [
    ("u1", "Hallitus leikkaa opintotukea", ""),
    ("u2", "Tyylitietoiset ottavat nyt mallia sipuleista", ""),
    ("u3", "De är årets luciakandidater", ""),
    ("u4", "Eduskunta äänesti sote-laista", ""),
]


def test_off_by_default_and_switchable(monkeypatch):
    assert scope_gate.enabled() is False
    monkeypatch.setenv("SCOPE_GATE", "on")
    assert scope_gate.enabled() is True
    monkeypatch.setenv("SCOPE_GATE", "off")
    assert scope_gate.enabled() is False


def test_default_model_is_a_general_model(monkeypatch):
    assert scope_gate._model() == "codestral-2508"
    monkeypatch.setenv("SCOPE_GATE_MODEL", "mistral-medium-latest")
    assert scope_gate._model() == "mistral-medium-latest"


def test_drops_and_keeps_per_the_model_and_one_call_per_batch(monkeypatch):
    calls = fake_model(monkeypatch, verdict_json(["sipuleista", "luciakandidater"]))
    verdicts = scope_gate.classify(ITEMS)
    assert [verdicts[k][0] for k in ("u1", "u2", "u3", "u4")] == [True, False, False, True]
    assert len(calls) == 1
    assert calls[0]["titles"][0] == "Hallitus leikkaa opintotukea"


def test_prompt_is_conservative():
    assert "If you are unsure, KEEP" in scope_gate.SYSTEM_PROMPT


def test_summary_is_truncated_and_html_stripped(monkeypatch):
    calls = fake_model(monkeypatch, verdict_json([]))
    long_summary = "<p>" + "x" * 500 + "</p>"
    scope_gate.classify([("u1", "Otsikko", long_summary)])
    line = calls[0]["user"].splitlines()[1]
    assert "<p>" not in line and len(line) < 200


def test_verdicts_are_cached_per_url(monkeypatch):
    calls = fake_model(monkeypatch, verdict_json(["sipuleista"]))
    scope_gate.classify(ITEMS)
    scope_gate.classify(ITEMS)  # second hour, same feed
    assert len(calls) == 1


def test_only_unseen_entries_are_sent(monkeypatch):
    calls = fake_model(monkeypatch, verdict_json([]))
    scope_gate.classify(ITEMS[:2])
    scope_gate.classify(ITEMS)
    assert len(calls) == 2
    assert calls[1]["titles"] == [ITEMS[2][1], ITEMS[3][1]]


def test_large_feeds_are_split_into_batches(monkeypatch):
    calls = fake_model(monkeypatch, verdict_json([]))
    many = [(f"u{i}", f"Otsikko {i}", "") for i in range(95)]
    verdicts = scope_gate.classify(many)
    assert len(verdicts) == 95
    assert [len(c["titles"]) for c in calls] == [40, 40, 15]


def test_string_booleans_are_understood(monkeypatch):
    fake_model(
        monkeypatch,
        lambda titles: json.dumps(
            {"results": [{"id": 1, "keep": "false", "why": "x"}, {"id": 2, "keep": "keep"}]}
        ),
    )
    verdicts = scope_gate.classify([("a", "A", ""), ("b", "B", "")])
    assert verdicts["a"][0] is False and verdicts["b"][0] is True


def test_code_fenced_json_is_accepted(monkeypatch):
    fake_model(
        monkeypatch,
        lambda t: (
            "```json\n"
            + json.dumps({"results": [{"id": 1, "keep": False, "why": "sports"}]})
            + "\n```"
        ),
    )
    assert scope_gate.classify([("a", "A", "")])["a"] == (False, "sports")


# --- fail open: a broken model must never remove coverage -----------------------------------


def test_exception_keeps_everything_and_caches_nothing(monkeypatch):
    def boom(system, user, max_tokens):
        raise TimeoutError("mistral timed out")

    monkeypatch.setattr(scope_gate, "_complete", boom)
    verdicts = scope_gate.classify(ITEMS)
    assert all(keep for keep, _ in verdicts.values())
    assert scope_gate._cache == {}


@pytest.mark.parametrize(
    "garbage", ["", "sorry I cannot", "[]", '{"results": "no"}', "{not json", '{"results": [1, 2]}']
)
def test_garbage_answers_keep_everything(monkeypatch, garbage):
    fake_model(monkeypatch, lambda titles: garbage)
    verdicts = scope_gate.classify(ITEMS)
    assert all(keep for keep, _ in verdicts.values())
    assert scope_gate._cache == {}


def test_missing_ids_are_kept_and_not_cached(monkeypatch):
    fake_model(
        monkeypatch, lambda t: json.dumps({"results": [{"id": 2, "keep": False, "why": "x"}]})
    )
    verdicts = scope_gate.classify(ITEMS)
    assert verdicts["u2"][0] is False
    assert verdicts["u1"] == (True, "no-verdict") and "u1" not in scope_gate._cache


def test_out_of_range_ids_are_ignored(monkeypatch):
    fake_model(
        monkeypatch,
        lambda t: json.dumps({"results": [{"id": 99, "keep": False}, {"id": 0, "keep": False}]}),
    )
    assert all(keep for keep, _ in scope_gate.classify(ITEMS).values())
