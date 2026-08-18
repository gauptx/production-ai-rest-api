# Production AI REST API

Milestone 1 adds PostgreSQL-backed identity and persistence to the local
FastAPI baseline: registration, login, refresh-token rotation, a protected
route, versioned database migrations, tests, linting, formatting, Docker
Compose, and continuous integration.

## Prerequisites

- Python 3.12+
- Docker Desktop (or Docker Engine with Docker Compose)

## Local setup

Create the local environment file:

```bash
cp .env.example .env
```

Create and activate a virtual environment, then install development dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
```

Start the local stack:

```bash
docker compose up --build
```

In a separate terminal, confirm the API is available:

```bash
curl http://localhost:8000/api/v1/health
```

Interactive API documentation is available at
`http://localhost:8000/api/v1/docs`.

The API container applies migrations before it starts. To run them explicitly:

```bash
docker compose run --rm api alembic upgrade head
```

Expected response:

```json
{"status":"ok"}
```

Stop the stack with `docker compose down`. Add `--volumes` only when you also
want to remove the local PostgreSQL and Redis data.

## Quality checks

Run these from the repository root with the virtual environment active:

```bash
ruff check .
ruff format --check .
pytest
```

GitHub Actions runs the same checks for every push and pull request.

## Authentication API

All authentication routes are versioned under `/api/v1/auth`.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/register` | Create a user and receive access and refresh tokens. |
| `POST` | `/login` | Exchange email and password for a fresh token pair. |
| `POST` | `/refresh` | Rotate a refresh token and receive a new token pair. |
| `GET` | `/me` | Verify an access token and return the authenticated user. |
| `POST` | `/api/v1/summaries` | Persist a queued summary job for the authenticated user. |
| `GET` | `/api/v1/summaries/{id}` | Retrieve the authenticated user's own summary job. |

Example registration:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"person@example.com","password":"correct-horse-battery"}'
```

Access tokens last 15 minutes by default. Refresh tokens last 7 days, are
stored only as password hashes, and rotate on use; a replayed token is rejected.
Set a unique, long `JWT_SECRET` outside local development.

Create a queued summary job with an access token:

```bash
curl -X POST http://localhost:8000/api/v1/summaries \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access_token>' \
  -d '{"text":"A short document to summarize later."}'
```

The endpoint persists the job with a `queued` status. Background queue and LLM
processing are deliberately deferred to Milestone 2.

## Scope boundary

`GET /api/v1/health` verifies that the API process is running. Dependency
readiness checks are intentionally deferred to a later milestone. All public
API routes use the `/api/v1` prefix.
