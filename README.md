# Production AI REST API

Milestone 0 establishes a local FastAPI baseline with PostgreSQL, Redis, tests,
linting, formatting, Docker Compose, and continuous integration.

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

## Scope boundary

`GET /api/v1/health` verifies that the API process is running. Dependency
readiness checks and application persistence are intentionally deferred to
later milestones. All public API routes use the `/api/v1` prefix.
