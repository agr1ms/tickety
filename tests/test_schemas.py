import pytest
from pydantic import ValidationError

from app.schemas import TicketCreate


def test_valid_ticket():
    t = TicketCreate(
        customer_email="a@b.com", subject="Hello", body="long enough body"
    )
    assert t.subject == "Hello"


def test_rejects_bad_email():
    with pytest.raises(ValidationError):
        TicketCreate(customer_email="nope", subject="Hello", body="long enough body")


@pytest.mark.parametrize("subject", ["", "ab", "x" * 121])
def test_rejects_bad_subject_length(subject):
    with pytest.raises(ValidationError):
        TicketCreate(
            customer_email="a@b.com", subject=subject, body="long enough body"
        )
