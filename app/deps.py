from typing import Annotated

import asyncpg
from fastapi import Depends, Request
from redis.asyncio import Redis

from .cache import hit_rate_limit
from .config import settings
from .db import TicketRepo
from .errors import RateLimitExceeded


def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_repo(pool: Annotated[asyncpg.Pool, Depends(get_pool)]) -> TicketRepo:
    return TicketRepo(pool)


RedisDep = Annotated[Redis, Depends(get_redis)]
RepoDep = Annotated[TicketRepo, Depends(get_repo)]


async def rate_limit(request: Request, redis: RedisDep) -> None:
    client = request.client.host if request.client else "unknown"
    limited, retry_after = await hit_rate_limit(
        redis, client, settings.rate_limit_per_minute
    )
    if limited:
        raise RateLimitExceeded(retry_after)
