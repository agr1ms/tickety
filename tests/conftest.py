from collections import Counter
from datetime import datetime, timezone

import pytest
from fakeredis import FakeAsyncRedis, FakeServer
from httpx import ASGITransport, AsyncClient

from app import enrichers
from app.deps import get_redis, get_repo
from app.main import app
from app.schemas import Stats, TicketOut


class InMemoryRepo:
    """Same interface as TicketRepo, but no database needed."""

    def __init__(self):
        self.tickets: list[TicketOut] = []

    async def insert_ticket(self, data, e):
        ticket = TicketOut(
            id=len(self.tickets) + 1,
            customer_email=data.customer_email,
            subject=data.subject,
            body=data.body,
            category=e.category,
            priority=e.priority,
            customer_tier=e.customer_tier,
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        self.tickets.append(ticket)
        return ticket

    async def get_ticket(self, ticket_id):
        return next((t for t in self.tickets if t.id == ticket_id), None)

    async def list_tickets(self, status, limit):
        items = [t for t in self.tickets if status is None or t.status == status]
        return list(reversed(items))[:limit]

    async def get_stats(self):
        by_category = Counter(t.category.value for t in self.tickets)
        by_priority = Counter(t.priority.value for t in self.tickets)
        return Stats(
            total=len(self.tickets),
            by_category=dict(by_category),
            by_priority=dict(by_priority),
        )


@pytest.fixture(autouse=True)
def fast_enrichers(monkeypatch):
    """Every test runs with no fake latency and no random CRM failures."""
    monkeypatch.setattr(enrichers, "LATENCY_SCALE", 0)
    monkeypatch.setattr(enrichers, "FAILURE_RATE", 0)


@pytest.fixture
def repo():
    return InMemoryRepo()


@pytest.fixture
def redis():
    return FakeAsyncRedis(server=FakeServer(), decode_responses=True)


@pytest.fixture
async def client(repo, redis):
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_redis] = lambda: redis
    # ASGITransport doesn't run lifespan, so no real DB/Redis connections happen
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
