# Production AI REST API

A production-focused, asynchronous text-summarization API. Authenticated users
submit text, the API persists and enqueues a job, and an ARQ worker uses local
Ollama to generate and persist the result. The service includes PostgreSQL
persistence, Redis-backed jobs, JWT authentication, refresh-token rotation,
Docker Compose, tests, linting, and formatting.

## Prerequisites

- Python 3.12+
- Docker Desktop (or Docker Engine with Docker Compose)
- [Ollama](https://ollama.com/download) with the local `gemma3:4b` model

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

Download the local model once:

```bash
ollama pull gemma3:4b
```

Confirm that Ollama can serve it locally:

```bash
ollama run gemma3:4b
```

Exit the interactive prompt with `Ctrl+D`. Ollama continues to provide its API
at `http://localhost:11434` while its app or service is running.

Start the local stack:

```bash
docker compose up --build
```

Compose starts four services: the API, PostgreSQL, Redis, and the ARQ worker.
The worker connects to Ollama running on the host through
`host.docker.internal:11434`.

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

## Configuration

`.env.example` contains safe local defaults for the database, Redis, JWT
settings, and Ollama model selection. Never commit a real `.env` file or
production credentials.

| Variable | Local default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama API address when running outside Compose. |
| `OLLAMA_MODEL` | `gemma3:4b` | Model used by the summary worker. |
| `REDIS_URL` | `redis://localhost:6379/0` | ARQ queue connection when running outside Compose. |

Docker Compose overrides the Ollama and Redis URLs so containers can reach the
host model service and the Redis container.

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
| `POST` | `/api/v1/auth/register` | Create a user and receive access and refresh tokens. |
| `POST` | `/api/v1/auth/login` | Exchange email and password for a fresh token pair. |
| `POST` | `/api/v1/auth/refresh` | Rotate a refresh token and receive a new token pair. |
| `GET` | `/api/v1/auth/me` | Verify an access token and return the authenticated user. |
| `POST` | `/api/v1/summaries` | Persist and enqueue a summary job for the authenticated user. |
| `GET` | `/api/v1/summaries/{id}` | Retrieve the authenticated user's own job state and result. |

Example registration:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"person@example.com","password":"correct-horse-battery"}'
```

Access tokens last 15 minutes by default. Refresh tokens last 7 days, are
stored only as password hashes, and rotate on use; a replayed token is rejected.
Set a unique, long `JWT_SECRET` outside local development.

Create a summary job with an access token:

```bash
curl -X POST http://localhost:8000/api/v1/summaries \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access_token>' \
  -d '{"text":"A short document to summarize later."}'
```

The API persists the job before it enqueues it. A successful response initially
contains the job ID and usually a `queued` status. The worker processes the job
asynchronously, so use the ID to poll for the final result:

```bash
curl http://localhost:8000/api/v1/summaries/<job_id> \
  -H 'Authorization: Bearer <access_token>'
```

Successful jobs return `completed` and include `result`. Failed jobs return
`failed` with a safe `failure_code`; raw provider errors are never returned to
the client.

## Asynchronous job processing

The state flow is:

```text
queued -> processing -> completed
                    -> failed
```

The API uses Redis and ARQ to dispatch jobs to the worker. The worker calls
local Ollama with `gemma3:4b`, then persists the generated summary in
PostgreSQL. If the queue cannot accept a job, the API returns `503` and records
`queue_unavailable` on the job.

Transient Ollama connectivity failures and 5xx responses are retried up to
three total attempts, with two- and five-second delays. A final transient
failure is recorded as `provider_unavailable`. Non-transient provider failures
are recorded as `provider_error`.

## Scope boundary

`GET /api/v1/health` verifies that the API process is running. Dependency
readiness checks are intentionally deferred to a later milestone. All public
API routes use the `/api/v1` prefix.
