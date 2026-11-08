"""Tests for the shared Mistral pacing module. No network, no real sleeping."""

from __future__ import annotations

import pytest

from src import mistral_limiter as ml


class FakeTime:
    """A clock that only moves when somebody sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for key in list(os.environ):
        if key.startswith(("MISTRAL_RPM_", "MISTRAL_TPM_")):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def fake() -> FakeTime:
    return FakeTime()


@pytest.fixture()
def limiter(fake: FakeTime) -> ml.RateLimiter:
    return ml.RateLimiter(clock=fake.clock, sleep=fake.sleep)


def _starts(
    limiter_: ml.RateLimiter, fake: FakeTime, model: str, n: int, tokens: int = 0
) -> list[float]:
    stamps = []
    for _ in range(n):
        limiter_.acquire(model, tokens)
        stamps.append(fake.now)
    return stamps


# --- requests per minute ----------------------------------------------------------


def test_codestral_is_paced_to_two_requests_a_minute(limiter, fake):
    stamps = _starts(limiter, fake, "codestral-2508", 6)
    for i, stamp in enumerate(stamps):
        window = [s for s in stamps if stamp - 60 < s <= stamp]
        assert len(window) <= 2, f"{len(window)} calls inside one minute at call {i}"
    # 6 calls need 5 gaps of 60 / (2 * 0.9) = 33.3 s
    assert stamps[-1] - stamps[0] == pytest.approx(5 * 60 / 1.8)


def test_first_call_does_not_wait(limiter, fake):
    assert limiter.acquire("codestral-2508", 100) == 0.0
    assert fake.slept == []


def test_models_are_paced_independently(limiter, fake):
    limiter.acquire("codestral-2508", 100)
    waited = limiter.acquire("codestral-embed", 100)
    assert waited == 0.0


def test_embedding_model_allows_many_calls(limiter, fake):
    stamps = _starts(limiter, fake, "codestral-embed", 10, tokens=300)
    assert stamps[-1] - stamps[0] == pytest.approx(9 * 60 / 45)  # 50 rpm * 0.9 = 45


def test_environment_raises_the_allowance(limiter, fake, monkeypatch):
    monkeypatch.setenv("MISTRAL_RPM_CODESTRAL_2508", "120")
    stamps = _starts(limiter, fake, "codestral-2508", 3)
    assert stamps[-1] - stamps[0] == pytest.approx(2 * 60 / 108)


def test_unknown_model_uses_the_fallback_and_default_env(limiter, fake, monkeypatch):
    assert ml.limits_for("some-new-model") == (30, 20_000)
    monkeypatch.setenv("MISTRAL_RPM_DEFAULT", "10")
    monkeypatch.setenv("MISTRAL_TPM_DEFAULT", "5000")
    assert ml.limits_for("some-new-model") == (10, 5000)
    # a built-in model ignores the generic default
    assert ml.limits_for("codestral-2508") == (2, 40_000)


@pytest.mark.parametrize("bad", ["abc", "", "0", "-5"])
def test_unusable_environment_values_are_ignored(bad, monkeypatch):
    monkeypatch.setenv("MISTRAL_RPM_CODESTRAL_2508", bad)
    assert ml.limits_for("codestral-2508") == (2, 40_000)


# --- tokens per minute ------------------------------------------------------------


def test_token_budget_holds_back_a_second_big_call(limiter, fake, monkeypatch):
    monkeypatch.setenv("MISTRAL_RPM_TESTMODEL", "6000")  # requests are not the limit here
    monkeypatch.setenv("MISTRAL_TPM_TESTMODEL", "1000")  # budget = 900 tokens per minute
    first = fake.now
    limiter.acquire("testmodel", 500)
    limiter.acquire("testmodel", 500)  # 1000 > 900, must wait until the first ages out
    assert fake.now - first == pytest.approx(60.0)


def test_small_calls_fit_inside_the_token_budget(limiter, fake, monkeypatch):
    monkeypatch.setenv("MISTRAL_RPM_TESTMODEL", "6000")
    monkeypatch.setenv("MISTRAL_TPM_TESTMODEL", "1000")
    start = fake.now
    for _ in range(3):
        limiter.acquire("testmodel", 200)  # 600 <= 900
    assert fake.now - start < 5


def test_a_request_bigger_than_the_whole_budget_is_not_stuck_forever(limiter, fake, monkeypatch):
    monkeypatch.setenv("MISTRAL_TPM_TESTMODEL", "1000")
    assert limiter.acquire("testmodel", 50_000) == 0.0


# --- penalty after a 429 -----------------------------------------------------------


def test_penalty_blocks_the_model_for_a_full_window(limiter, fake):
    limiter.acquire("codestral-2508", 10)
    limiter.penalize("codestral-2508")
    before = fake.now
    limiter.acquire("codestral-2508", 10)
    assert fake.now - before == pytest.approx(ml.PENALTY_SECONDS)


def test_penalty_does_not_touch_other_models(limiter, fake):
    limiter.penalize("codestral-2508")
    assert limiter.acquire("codestral-embed", 10) == 0.0


def test_a_shorter_penalty_never_shortens_a_longer_one(limiter, fake):
    limiter.penalize("codestral-2508", 100)
    limiter.penalize("codestral-2508", 5)
    before = fake.now
    limiter.acquire("codestral-2508", 10)
    assert fake.now - before == pytest.approx(100)


# --- token estimate ---------------------------------------------------------------


def test_token_estimate_is_conservative_and_never_zero():
    assert ml.estimate_tokens("") == 1
    assert ml.estimate_tokens("a" * 300) == 101
    assert ml.estimate_tokens("a" * 150, "b" * 150) == 101
