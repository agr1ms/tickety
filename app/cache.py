from redis.asyncio import Redis

from .schemas import Stats

STATS_KEY = "tickety:stats"


def create_redis(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True)


async def get_cached_stats(redis: Redis) -> Stats | None:
    raw = await redis.get(STATS_KEY)
    return Stats.model_validate_json(raw) if raw else None


async def set_cached_stats(redis: Redis, stats: Stats, ttl: int) -> None:
    await redis.set(STATS_KEY, stats.model_dump_json(), ex=ttl)


async def invalidate_stats(redis: Redis) -> None:
    await redis.delete(STATS_KEY)


async def hit_rate_limit(
    redis: Redis, client_id: str, limit: int, window: int = 60
) -> tuple[bool, int]:
    """Fixed-window counter. Returns (is_limited, seconds_until_reset)."""
    key = f"tickety:rl:{client_id}"
    count = await redis.incr(key)       # atomic: safe with concurrent requests
    if count == 1:
        await redis.expire(key, window) # window starts on the first hit
    ttl = await redis.ttl(key)
    return count > limit, max(ttl, 1)
