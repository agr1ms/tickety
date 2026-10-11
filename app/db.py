import asyncpg

from .enrichers import Enrichment
from .schemas import Stats, Status, TicketCreate, TicketOut


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class TicketRepo:
    """All SQL lives here. Routes never see SQL or asyncpg rows."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def insert_ticket(self, data: TicketCreate, e: Enrichment) -> TicketOut:
        row = await self.pool.fetchrow(
            """
            INSERT INTO tickets
                (customer_email, subject, body, category, priority, customer_tier)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            data.customer_email,
            data.subject,
            data.body,
            e.category.value,
            e.priority.value,
            e.customer_tier.value,
        )
        return TicketOut.model_validate(dict(row))

    async def get_ticket(self, ticket_id: int) -> TicketOut | None:
        row = await self.pool.fetchrow(
            "SELECT * FROM tickets WHERE id = $1", ticket_id
        )
        return TicketOut.model_validate(dict(row)) if row else None

    async def list_tickets(self, status: Status | None, limit: int) -> list[TicketOut]:
        if status is None:
            rows = await self.pool.fetch(
                "SELECT * FROM tickets ORDER BY id DESC LIMIT $1", limit
            )
        else:
            rows = await self.pool.fetch(
                "SELECT * FROM tickets WHERE status = $1 ORDER BY id DESC LIMIT $2",
                status.value,
                limit,
            )
        return [TicketOut.model_validate(dict(r)) for r in rows]

    async def get_stats(self) -> Stats:
        cat_rows = await self.pool.fetch(
            "SELECT category, COUNT(*) AS n FROM tickets GROUP BY category"
        )
        pri_rows = await self.pool.fetch(
            "SELECT priority, COUNT(*) AS n FROM tickets GROUP BY priority"
        )
        by_category = {r["category"]: r["n"] for r in cat_rows}
        by_priority = {r["priority"]: r["n"] for r in pri_rows}
        return Stats(
            total=sum(by_category.values()),
            by_category=by_category,
            by_priority=by_priority,
        )
