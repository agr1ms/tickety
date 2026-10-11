import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from . import cache
from .config import settings
from .db import create_pool
from .deps import RedisDep, RepoDep, rate_limit
from .enrichers import enrich
from .errors import RateLimitExceeded, TicketNotFound
from .schemas import Stats, Status, TicketCreate, TicketOut

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tickety")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create connections once, share them across all requests
    app.state.pool = await create_pool(settings.database_url)
    app.state.redis = cache.create_redis(settings.redis_url)
    yield
    # shutdown
    await app.state.pool.close()
    await app.state.redis.aclose()


app = FastAPI(title="Tickety", lifespan=lifespan)


@app.exception_handler(TicketNotFound)
async def handle_not_found(request: Request, exc: TicketNotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(RateLimitExceeded)
async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": str(exc.retry_after)},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post(
    "/tickets",
    response_model=TicketOut,
    status_code=201,
    dependencies=[Depends(rate_limit)],
)
async def create_ticket(payload: TicketCreate, repo: RepoDep, redis: RedisDep):
    start = time.perf_counter()
    enrichment = await enrich(payload.subject, payload.body, payload.customer_email)
    ticket = await repo.insert_ticket(payload, enrichment)
    await cache.invalidate_stats(redis)  # cached stats are now stale
    logger.info("ticket %s created in %.2fs", ticket.id, time.perf_counter() - start)
    return ticket


@app.get("/tickets/{ticket_id}", response_model=TicketOut)
async def read_ticket(ticket_id: int, repo: RepoDep):
    ticket = await repo.get_ticket(ticket_id)
    if ticket is None:
        raise TicketNotFound(ticket_id)
    return ticket


@app.get("/tickets", response_model=list[TicketOut])
async def list_tickets(
    repo: RepoDep,
    status: Status | None = None,
    limit: int = Query(10, ge=1, le=100),
):
    return await repo.list_tickets(status, limit)


@app.get("/stats", response_model=Stats)
async def stats(repo: RepoDep, redis: RedisDep):
    cached = await cache.get_cached_stats(redis)
    if cached is not None:
        logger.info("stats: cache HIT")
        return cached
    logger.info("stats: cache MISS")
    fresh = await repo.get_stats()
    await cache.set_cached_stats(redis, fresh, settings.stats_cache_ttl)
    return fresh
