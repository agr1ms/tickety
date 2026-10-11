import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from .errors import LookupFailed
from .schemas import Category, CustomerTier, Priority

T = TypeVar("T")

# Knobs that tests can turn down (see conftest.py)
LATENCY_SCALE = 1.0
FAILURE_RATE = 0.2

CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.billing: ["invoice", "charge", "refund", "payment"],
    Category.bug: ["error", "crash", "broken", "exception"],
    Category.account: ["password", "login", "locked", "account"],
}
URGENT_WORDS = ["urgent", "asap", "down", "outage", "immediately"]
ENTERPRISE_DOMAINS = {"bigcorp.com"}
PRO_DOMAINS = {"startup.io"}


@dataclass(frozen=True)
class Enrichment:
    category: Category
    priority: Priority
    customer_tier: CustomerTier


async def categorize(text: str) -> Category:
    await asyncio.sleep(0.3 * LATENCY_SCALE)  # pretend this is a model call
    lowered = text.lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if any(word in lowered for word in words):
            return category
    return Category.general


async def score_priority(text: str) -> Priority:
    await asyncio.sleep(0.3 * LATENCY_SCALE)
    lowered = text.lower()
    hits = sum(word in lowered for word in URGENT_WORDS)  # True counts as 1
    if hits >= 2:
        return Priority.high
    if hits == 1:
        return Priority.medium
    return Priority.low


async def lookup_customer_tier(email: str) -> CustomerTier:
    await asyncio.sleep(0.5 * LATENCY_SCALE)  # pretend this is a CRM call
    if random.random() < FAILURE_RATE:
        raise LookupFailed(f"CRM lookup failed for {email}")
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in ENTERPRISE_DOMAINS:
        return CustomerTier.enterprise
    if domain in PRO_DOMAINS:
        return CustomerTier.pro
    return CustomerTier.free


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    attempts: int = 3,
    delay: float = 0.1,
) -> T:
    """Call an async function, retrying LookupFailed with growing delays."""
    for attempt in range(1, attempts + 1):
        try:
            return await func(*args)
        except LookupFailed:
            if attempt == attempts:
                raise
            await asyncio.sleep(delay * attempt)
    raise RuntimeError("unreachable")  # keeps type checkers happy


async def safe_tier_lookup(email: str) -> CustomerTier:
    """Graceful degradation: if the CRM is down, treat them as 'free'."""
    try:
        return await with_retry(lookup_customer_tier, email)
    except LookupFailed:
        return CustomerTier.free


async def enrich(subject: str, body: str, email: str) -> Enrichment:
    text = f"{subject} {body}"
    category, priority, tier = await asyncio.gather(
        categorize(text),
        score_priority(text),
        safe_tier_lookup(email),
    )
    return Enrichment(category, priority, tier)
