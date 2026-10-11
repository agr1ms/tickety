from app.cache import STATS_KEY
from app.config import settings

VALID = {
    "customer_email": "ana@bigcorp.com",
    "subject": "Double charge",
    "body": "I was charged twice, refund this payment urgent asap",
}


async def test_create_ticket_is_enriched(client):
    r = await client.post("/tickets", json=VALID)
    assert r.status_code == 201
    data = r.json()
    assert data["category"] == "billing"
    assert data["priority"] == "high"
    assert data["customer_tier"] == "enterprise"
    assert data["status"] == "open"


async def test_invalid_payload_returns_422(client):
    bad = {"customer_email": "nope", "subject": "x", "body": "short"}
    r = await client.post("/tickets", json=bad)
    assert r.status_code == 422


async def test_get_missing_ticket_returns_404(client):
    r = await client.get("/tickets/999")
    assert r.status_code == 404
    assert "999" in r.json()["detail"]


async def test_list_respects_limit(client):
    await client.post("/tickets", json=VALID)
    await client.post("/tickets", json=VALID)
    r = await client.get("/tickets", params={"limit": 1})
    assert len(r.json()) == 1


async def test_stats_are_cached_then_invalidated(client, redis):
    await client.post("/tickets", json=VALID)

    first = await client.get("/stats")
    assert first.json()["total"] == 1
    assert await redis.get(STATS_KEY) is not None   # cache filled

    await client.post("/tickets", json=VALID)
    assert await redis.get(STATS_KEY) is None       # cache invalidated

    second = await client.get("/stats")
    assert second.json()["total"] == 2              # fresh data, not stale


async def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    codes = [(await client.post("/tickets", json=VALID)).status_code for _ in range(4)]
    assert codes == [201, 201, 201, 429]

    r = await client.post("/tickets", json=VALID)
    assert "retry-after" in r.headers
