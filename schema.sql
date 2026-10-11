CREATE TABLE IF NOT EXISTS tickets (
    id             SERIAL PRIMARY KEY,
    customer_email TEXT NOT NULL,
    subject        TEXT NOT NULL,
    body           TEXT NOT NULL,
    category       TEXT NOT NULL,
    priority       TEXT NOT NULL,
    customer_tier  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'open',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status);
