import time

import pytest

from app import enrichers
from app.errors import LookupFailed
from app.schemas import Category, CustomerTier, Priority


@pytest.mark.parametrize(
    "text, expected",
    [
        ("I need a refund for this invoice", Category.billing),
        ("app crash with error", Category.bug),
        ("forgot password", Category.account),
        ("hello there", Category.general),
    ],
)
async def test_categorize(text, expected):
    assert await enrichers.categorize(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("everything is fine", Priority.low),
        ("urgent please", Priority.medium),
        ("urgent, system down asap", Priority.high),
    ],
)
async def test_score_priority(text, expected):
    assert await enrichers.score_priority(text) == expected


async def test_with_retry_succeeds_after_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise LookupFailed("boom")
        return "ok"

    assert await enrichers.with_retry(flaky, attempts=3, delay=0) == "ok"
    assert calls["n"] == 3


async def test_with_retry_gives_up():
    async def always_fails():
        raise LookupFailed("boom")

    with pytest.raises(LookupFailed):
        await enrichers.with_retry(always_fails, attempts=2, delay=0)


async def test_tier_falls_back_to_free_when_crm_down(monkeypatch):
    monkeypatch.setattr(enrichers, "FAILURE_RATE", 1.0)  # always fail
    assert await enrichers.safe_tier_lookup("a@bigcorp.com") == CustomerTier.free


async def test_enrich_runs_concurrently(monkeypatch):
    monkeypatch.setattr(enrichers, "LATENCY_SCALE", 1)  # real delays: 0.3+0.3+0.5
    start = time.perf_counter()
    await enrichers.enrich("Hi there", "some body text here", "a@b.com")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.9  # sequential would be ~1.1s
