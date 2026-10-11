class TicketyError(Exception):
    """Base class so we can catch all our own errors at once."""


class TicketNotFound(TicketyError):
    def __init__(self, ticket_id: int):
        self.ticket_id = ticket_id
        super().__init__(f"Ticket {ticket_id} not found")


class RateLimitExceeded(TicketyError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry in {retry_after}s")


class LookupFailed(TicketyError):
    """Simulates a flaky external system (like a CRM)."""
