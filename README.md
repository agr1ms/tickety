# Tickety: Ticket Triage Service

Support tickets arrive as an email, subject and body. Tickety validates them, enriches each one
(category, priority, customer tier) using three slow/flaky lookups run **concurrently**, stores it in
Postgres, and exposes a REST API with a cached stats endpoint and a per-client rate limiter.

## Architecture

```
Client -> FastAPI (validation, rate limit via Redis)
            |-> enrichers: asyncio.gather(categorize, score_priority, safe_tier_lookup)
            |-> Postgres (asyncpg pool): source of truth
            '-> Redis: /stats cache (TTL) + fixed-window rate limiter
```

## Run it

```bash
cp .env.example .env        # then set real values
docker compose up --build
curl localhost:8000/health
curl -X POST localhost:8000/tickets -H "Content-Type: application/json" \
  -d '{"customer_email":"ana@bigcorp.com","subject":"Double charge","body":"I was charged twice, refund this payment urgent asap"}'
```
Interactive docs: http://localhost:8000/docs

Local dev with reload: `docker compose up db redis -d && uvicorn app.main:app --reload`

## Run tests

```bash
pip install -r requirements-dev.txt && pytest
```
No Docker needed: tests swap the repo and Redis for in-memory fakes via FastAPI dependency overrides.

## Module checklist

| Module topic | Where |
|---|---|
| Types, functions, comprehensions, errors | `schemas.py`, `enrichers.py`, `errors.py`, `db.py` |
| async/await + concurrency | `enrichers.py` (`gather`), `test_enrich_runs_concurrently` |
| Pydantic | `schemas.py`, `config.py` |
| FastAPI + DI | `main.py`, `deps.py` |
| pytest + fixtures | `tests/` |
| Docker | `Dockerfile`, `docker-compose.yml` |
| Postgres + Redis | `db.py`, `schema.sql`, `cache.py` |
| Env + secrets | `.env`, `.env.example`, `config.py`, `.gitignore` |

## Design decisions and limitations

- Raw SQL with asyncpg (parameterized `$1`) instead of an ORM, to keep the data layer visible.
- If the CRM lookup keeps failing, the tier degrades to `free` instead of failing ticket creation.
- Rate limiter is a fixed-window counter; a crash between `INCR` and `EXPIRE` leaves a key without TTL.
  Production would use a Lua script or pipeline.
- `schema.sql` only runs on first volume creation; there are no migrations.

## What I'd do next

Alembic migrations, structured logging, auth, CI pipeline.
