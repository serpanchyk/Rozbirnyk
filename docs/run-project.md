# Run Rozbirnyk

This document is the canonical startup guide for Rozbirnyk in local development.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+ and `npm`
- Docker and Docker Compose with the Docker daemon running
- `TAVILY_API_KEY` for `news_service`
- AWS credentials plus a Bedrock-compatible model or inference profile ID for
  `agent_service`

## Install Dependencies

Sync Python workspace dependencies from the repo root:

```bash
uv sync
```

Install frontend dependencies:

```bash
cd apps/frontend
npm install
cd ../..
```

## Docker Quick Start

Copy the shared Docker Compose environment file:

```bash
cp .env.example .env
```

Fill in the required values in `.env`:

```bash
TAVILY_API_KEY=replace-me
```

The checked-in `.env.example` also defines the default host ports consumed by
`docker-compose.yaml`:

```bash
BACKEND_PORT=8000
FRONTEND_PORT=8501
VITE_BACKEND_URL=http://localhost:8000
```

Notes:

- Docker Compose auto-loads the repo-root `.env` for variable substitution, but
  only the Docker-specific settings declared in `docker-compose.yaml` are
  passed into containers.
- The default Docker startup path is idempotent: use `docker compose up --build
  -d` to build missing images, create missing containers, and recreate changed
  services without forcing a full teardown first.
- `TAVILY_API_KEY` is required for Compose startup. If it is missing, Compose
  stops before building the stack instead of starting a broken news service.
- `agent_service` now fails fast at startup if Bedrock config values are empty,
  if LangSmith tracing is enabled without a real API key, or if AWS
  credentials cannot be resolved from the normal provider chain.
- AWS credentials for `agent_service` are still expected from normal AWS
  environment variables, shared profiles, or IAM roles. Compose passes through
  standard AWS credential variables and mounts `${AWS_SHARED_CREDENTIALS_DIR}`
  or `${HOME}/.aws` read-only at `/root/.aws` so `AWS_PROFILE` works in the
  container.
- LangSmith tracing is optional. Leave
  `OBSERVABILITY__LANGSMITH__ENABLED=false` unless you want World Builder runs
  traced from `agent_service`.
- Service-local `.env.example` files remain available for direct per-service
  local runs; they are not required for Docker Compose startup.
- For direct local service runs, the Python services read `.env` from their own
  working directory through `BaseServiceConfig`.

## Configure Amazon Bedrock Access

`agent_service` uses AWS Bedrock through the normal AWS credential provider
chain. Do not put AWS secrets into the repo `.env` files.

Supported local approaches:

- Use `aws configure` and the default shared profile.
- Use a named shared profile and set `AWS_PROFILE=<profile-name>` in the
  repo-root `.env` or export it in the shell before starting Compose.
- Export temporary shell credentials such as `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN`.

Region handling:
- Bedrock model region is configured in `apps/agent_service/config.toml`.
- Override it for local runs with `MODEL__REGION_NAME=<aws-region>` in
  `apps/agent_service/.env` or in the shell.
- `MODEL__MODEL_ID` may be a raw foundation model ID, an inference profile ID,
  or an inference profile ARN. For Claude 4 local development, prefer an
  cross-region inference profile ID or ARN such as
  `us.anthropic.claude-sonnet-4-20250514-v1:0`.
- Keep the configured model/inference profile and region aligned with a region
  where that resource is enabled in your AWS account.

Bedrock runtime pacing and retry controls:
- `MODEL__RUNTIME__MAX_CONCURRENCY=1`
- `MODEL__RUNTIME__MIN_SECONDS_BETWEEN_CALLS=2.0`
- `MODEL__RUNTIME__MAX_RETRIES=10`
- `MODEL__RUNTIME__RETRY_BASE_SECONDS=1.0`
- `MODEL__RUNTIME__RETRY_MAX_SECONDS=60.0`

Recommended starting point:
- Keep `MODEL__MODEL_ID` on a cross-region inference profile for Docker and
  production-like runs.
- Start with concurrency `1` and a two-second minimum gap between Bedrock
  calls.
- Let the built-in retry path absorb transient `ThrottlingException` responses
  before the run is marked failed.

Minimal local verification:

```bash
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1
```

If `agent_service` fails at startup or on first model call:

- If startup fails immediately with an AWS credential resolution error, run
  `aws configure`, set `AWS_PROFILE`, export direct AWS credentials, or use an
  IAM role before retrying startup.
- Confirm the AWS identity has Bedrock permissions.
- Confirm the selected model or inference profile is enabled in the configured
  region.
- Confirm `MODEL__REGION_NAME` matches the region you are querying.
- If Bedrock reports that on-demand throughput is unsupported, switch
  `MODEL__MODEL_ID` to an inference profile ID or ARN instead of the raw
  foundation model ID.
- If World Builder still fails with Bedrock throttling, keep the inference
  profile target and lower request pressure further with
  `MODEL__RUNTIME__MAX_CONCURRENCY=1` and an even higher
  `MODEL__RUNTIME__MIN_SECONDS_BETWEEN_CALLS`.
- Docker Compose forwards repo-root `MODEL__...` variables into
  `agent-service`; use the repo-root `.env` instead of service-local `.env`
  files when tuning Bedrock pacing for container runs.
- If using Docker Compose with a shared credentials directory outside
  `${HOME}/.aws`, set `AWS_SHARED_CREDENTIALS_DIR=/path/to/.aws` in `.env`.
- If using Docker Compose with temporary credentials, export
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN` before
  `docker compose up --build`, or put them in a local uncommitted `.env`.

## Configure LangSmith Tracing

`agent_service` supports optional LangSmith tracing for World Builder workflow
runs.

Enable it in `apps/agent_service/.env`:

```bash
OBSERVABILITY__LANGSMITH__ENABLED=true
OBSERVABILITY__LANGSMITH__PROJECT=rozbirnyk
OBSERVABILITY__LANGSMITH__API_KEY=your-langsmith-api-key
```

Optional override:

```bash
OBSERVABILITY__LANGSMITH__ENDPOINT=https://api.smith.langchain.com
```

Notes:

- Tracing is emitted only by `agent_service` in this repo today.
- Leave tracing disabled when you do not want workflow data sent to LangSmith.
- Each traced World Builder run includes `session_id`, `run_id`, `max_actors`,
  and `max_state_files` metadata.

## Run The Full Stack With Docker

From the repo root, build and start the stack with:

```bash
docker compose up --build -d
```

Main URLs after startup:

- Frontend: `http://localhost:8501`
- Backend: `http://localhost:8000`
- `agent-service`, `news-service`, `wiki-service`, and `redis` are internal to
  the Compose network and are not published on host ports in the default setup.

Inspect logs with:

```bash
docker compose logs -f backend
```

Useful checks:

```bash
docker compose ps
docker compose logs -f
```

If you want to stop the running stack but keep containers and named volumes:

```bash
docker compose stop
```

If you want to remove the stack containers and networks for a fresh recreate:

```bash
docker compose down --remove-orphans
```

If you also want to remove named volumes such as the persisted wiki data:

```bash
docker compose down --remove-orphans --volumes
```

If Docker is not running, startup fails with an error like:

```text
Cannot connect to the Docker daemon
```

Start Docker Desktop or the system Docker service, then rerun
`docker compose up --build`.

If `docker compose up --build -d` reports a container recreation problem, first
inspect the stack:

```bash
docker compose ps
docker compose logs --tail 100
```

If Docker reports `permission denied` while stopping or recreating a container,
the daemon may have a stuck container process. Restart Docker from a privileged
shell and then rerun the normal startup command:

```bash
sudo systemctl restart docker
docker compose up --build -d
```

The Compose file intentionally does not set fixed `container_name` values. That
keeps startup and recreates more reliable by letting Compose manage container
replacement without hard name conflicts.

## Run Services Locally

Use this path only when you intentionally want to work on one service outside
Docker Compose.

Copy the service-local example files you need:

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/agent_service/.env.example apps/agent_service/.env
cp apps/frontend/.env.example apps/frontend/.env
cp mcp_servers/news_service/.env.example mcp_servers/news_service/.env
cp mcp_servers/wiki_service/.env.example mcp_servers/wiki_service/.env
```

Open a separate terminal for each service.

### Wiki service

```bash
cd mcp_servers/wiki_service
uv run python -m wiki_service.main
```

Runs on `http://localhost:8003` when started from the default config.
The checked-in `.env.example` already matches this local port.

### News service

```bash
cd mcp_servers/news_service
uv run python -m news_service.main
```

Runs on `http://localhost:8000` inside the service directory by default. If you
run it locally alongside backend on the same machine, start it with a host port
override:

```bash
cd mcp_servers/news_service
SERVICE__PORT=8002 uv run python -m news_service.main
```

Keep `mcp_servers/news_service/.env` at port `8000` for Docker Compose; use the
one-line shell override above for the standard local multi-service stack.

### Agent service

When running locally, override MCP hostnames to `localhost` and point the news
service to its SSE port.

```bash
cd apps/agent_service
MCP_SERVERS__WIKI_SERVICE__HOST=localhost \
MCP_SERVERS__WIKI_SERVICE__PORT=8003 \
MCP_SERVERS__NEWS_SERVICE__HOST=localhost \
MCP_SERVERS__NEWS_SERVICE__PORT=8002 \
uv run python -m agent_service.main
```

Runs on `http://localhost:8001`.

### Backend

When running locally, point backend upstream URLs at the localhost service ports.

```bash
cd apps/backend
UPSTREAM__AGENT_SERVICE_URL=http://localhost:8001 \
UPSTREAM__WIKI_SERVICE_URL=http://localhost:8003 \
uv run python -m backend.main
```

Runs on `http://localhost:8000`.

### Frontend

```bash
cd apps/frontend
npm run dev
```

Runs on `http://localhost:8501`.

The frontend reads `VITE_BACKEND_URL` from `apps/frontend/.env`. The default is:

```bash
VITE_BACKEND_URL=http://localhost:8000
```

## Verification

From the repo root:

```bash
uv run pre-commit run --all-files
uv run pytest
```

From `apps/frontend`:

```bash
npm test
npm run build
```
