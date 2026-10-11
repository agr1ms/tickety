from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class Category(StrEnum):
    billing = "billing"
    bug = "bug"
    account = "account"
    general = "general"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class CustomerTier(StrEnum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class Status(StrEnum):
    open = "open"
    closed = "closed"


class TicketCreate(BaseModel):
    customer_email: EmailStr
    subject: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=10, max_length=5000)


class TicketOut(BaseModel):
    id: int
    customer_email: str
    subject: str
    body: str
    category: Category
    priority: Priority
    customer_tier: CustomerTier
    status: Status
    created_at: datetime


class Stats(BaseModel):
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
