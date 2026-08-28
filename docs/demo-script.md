# Demo Script — Production AI REST API

**Length:** 2–3 minutes  
**Audience:** Hiring managers and technical leads  
**Goal:** Show a production-oriented asynchronous AI backend, not a UI demo.

## Before recording

- Use a fresh demo account and harmless sample text.
- Start with `/api/v1/health` and `/api/v1/readiness` already passing.
- Have the API documentation open at `/api/v1/docs` and a terminal ready for
  log output.
- Keep passwords, tokens, `.env` values, and provider responses that may contain
  sensitive text off screen.

## Script

| Time | Screen action | Narration |
|---|---|---|
| 0:00–0:20 | Show `docs/architecture.md`. | “This is an asynchronous text-summarization API. The FastAPI service authenticates requests, persists jobs in PostgreSQL, and places LLM work on Redis for a separate ARQ worker.” |
| 0:20–0:40 | Open `/api/v1/health`, then `/api/v1/readiness`. | “Health proves the API process is responding. Readiness separately checks PostgreSQL and Redis, so deployment automation can distinguish a running process from a usable service.” |
| 0:40–1:05 | In Swagger UI, register or log in with the demo account. | “The service uses short-lived JWT access tokens and rotating, hashed refresh tokens. Summary routes are authenticated and enforce ownership isolation.” |
| 1:05–1:35 | Call `POST /api/v1/summaries` with a short sample paragraph. Show the `201` response, job ID, `queued` status, and `X-Request-ID`. | “The API rate-limits submissions per user, writes the job before queueing it, and immediately returns a job ID. It does not hold the HTTP request open for LLM inference.” |
| 1:35–2:00 | Poll `GET /api/v1/summaries/{id}` until `completed`; show the result. | “The worker consumes the Redis job, calls the configured model, and persists a completed result. The client can poll safely for the terminal state.” |
| 2:00–2:25 | Show filtered API and worker logs using the job ID or request ID. | “Request and job correlation IDs connect API acceptance to asynchronous processing. Logs intentionally exclude request bodies, passwords, tokens, and raw provider errors.” |
| 2:25–2:45 | Briefly show the test/CI section of the README. | “The repository includes automated coverage for authentication, ownership, queue/provider failures, readiness, and rate limiting. The next delivery step is preserving this evidence in a deployed environment.” |

## Optional 20-second failure segment

If a controlled environment is available, temporarily make the Ollama endpoint
unreachable and submit one demo job. Show the terminal `failed` state with the
safe `provider_unavailable` code. Do not expose raw connection errors or leave
the deployed service in a broken state after recording.
