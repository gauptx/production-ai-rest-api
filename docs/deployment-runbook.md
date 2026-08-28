# Deployment Runbook — AWS Lightsail

**Status:** Draft for Milestone 4. This is a deployment plan, not evidence of a
live deployment.

## Target

- Platform: AWS Lightsail Linux/Ubuntu instance in Mumbai (`ap-south-1`).
- Capacity: 16 GB memory, 4 vCPU, 320 GB SSD for the initial Ollama-backed
  portfolio deployment.
- Runtime: Docker Compose, Caddy, FastAPI API, ARQ worker, PostgreSQL, Redis,
  and Ollama.

## Preconditions

1. Register a domain and create an `A` record pointing to the Lightsail static
   IP address.
2. Create the instance with an SSH key; enable automatic snapshots before the
   first release.
3. Configure the Lightsail firewall to allow only TCP 22, 80, and 443. Restrict
   SSH to a trusted IP range when possible.
4. Add production deployment assets to this repository before deploying:
   `compose.production.yaml`, `Caddyfile`, and `.env.production.example`.
   The current `docker-compose.yml` is local-development configuration and uses
   `host.docker.internal` for Ollama; do not use it unmodified on a VM.

## Server bootstrap

On the new Ubuntu host, install Docker Engine and the Docker Compose plugin,
then verify both commands are available:

```bash
docker --version
docker compose version
```

Create a restricted deployment user, clone the repository into that user's home
directory, and create a server-only `.env` file with at least:

```dotenv
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=<long-random-password>
JWT_SECRET=<long-random-secret>
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
OLLAMA_MODEL=gemma3:4b
SUMMARY_RATE_LIMIT=5
SUMMARY_RATE_LIMIT_WINDOW_SECONDS=60
```

Generate secrets on the server; do not paste sample values into source control:

```bash
openssl rand -base64 48
```

## Release procedure

After the production Compose and Caddy files exist, perform each release from
the repository root on the VM:

```bash
git fetch origin
git checkout <approved-release-ref>
git pull --ff-only origin <approved-release-ref>
docker compose -f docker-compose.yml -f compose.production.yaml config --quiet
docker compose -f docker-compose.yml -f compose.production.yaml build
docker compose -f docker-compose.yml -f compose.production.yaml run --rm api alembic upgrade head
docker compose -f docker-compose.yml -f compose.production.yaml up -d
docker compose -f docker-compose.yml -f compose.production.yaml ps
```

Pull the configured Ollama model once the Ollama service is running:

```bash
docker compose -f docker-compose.yml -f compose.production.yaml exec ollama ollama pull gemma3:4b
```

The production override must use the Docker service address `http://ollama:11434`
for both API and worker, keep data stores private, and configure restart
policies. Caddy should be the only public-facing container.

## Verification checklist

Run these from a machine outside the VM:

```bash
curl --fail --silent https://<domain>/api/v1/health
curl --fail --silent https://<domain>/api/v1/readiness
curl --fail --silent https://<domain>/api/v1/openapi.json > /dev/null
```

Then use the API documentation at `https://<domain>/api/v1/docs` to register a
fresh demo user, create a summary job, and poll it until it is `completed`.
Confirm that:

- `/health` and `/readiness` return `{"status":"ok"}`.
- The API response contains `X-Request-ID`.
- Worker logs contain the job ID and no request body, password, token, or raw
  provider error.
- PostgreSQL and Ollama data survive a container restart.

## Rollback and recovery

1. Stop the release if readiness fails; do not expose a deployment with failed
   dependencies.
2. Return to the previous approved Git ref and repeat the release procedure.
3. Do not roll back a migration by deleting data. Restore from a tested snapshot
   or write an explicit downgrade only when it is safe.
4. Record the release ref, deployment URL, verification date, and any incident
   in the Milestone 4 evidence record.
