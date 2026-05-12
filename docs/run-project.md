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
AGENT_SERVICE_PORT=8001
NEWS_SERVICE_PORT=8002
WIKI_SERVICE_PORT=8003
FRONTEND_PORT=8501
REDIS_PORT=6379
VITE_BACKEND_URL=http://localhost:8000
```

Notes:

- Docker Compose auto-loads the repo-root `.env` for variable substitution, but
  only the Docker-specific settings declared in `docker-compose.yaml` are
  passed into containers.
- `TAVILY_API_KEY` is required for Compose startup. If it is missing, Compose
  stops before building the stack instead of starting a broken news service.
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
- For direct local service runs, the Python services read `.env` from their own working directory through `BaseServiceConfig`.

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
  inference profile ID or ARN such as
  `us.anthropic.claude-sonnet-4-20250514-v1:0`.
- Keep the configured model/inference profile and region aligned with a region
  where that resource is enabled in your AWS account.

Minimal local verification:

```bash
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1
```

If `agent_service` fails at startup or on first model call:

- Confirm the AWS identity has Bedrock permissions.
- Confirm the selected model or inference profile is enabled in the configured
  region.
- Confirm `MODEL__REGION_NAME` matches the region you are querying.
- If Bedrock reports that on-demand throughput is unsupported, switch
  `MODEL__MODEL_ID` to an inference profile ID or ARN instead of the raw
  foundation model ID.
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

From the repo root:

```bash
docker compose up --build
```

Main URLs after startup:

- Frontend: `http://localhost:8501`
- Backend: `http://localhost:8000`
- Agent service: `http://localhost:8001`
- News service: `http://localhost:8002`
- Wiki service: `http://localhost:8003`

Inspect logs with:

```bash
docker compose logs -f backend
```

If you want a shorter restart command after the first build:

```bash
docker compose up
```

Useful checks:

```bash
docker compose ps
docker compose logs -f
```

If Docker is not running, startup fails with an error like:

```text
Cannot connect to the Docker daemon
```

Start Docker Desktop or the system Docker service, then rerun
`docker compose up --build`.

If the system Docker service is running but the active Docker context points to
an inactive Docker Desktop socket, either switch contexts:

```bash
docker context use default
```

or run Compose with the system daemon for only that command:

```bash
DOCKER_CONTEXT=default docker compose up --build
```

If Docker reports `permission denied` while stopping or recreating a container,
the daemon may have a stuck container process. Check the current stack with
`docker compose ps`. If containers remain healthy, the app is still usable; to
recover clean recreate behavior, restart Docker from a privileged shell and run
Compose again:

```bash
sudo systemctl restart docker
DOCKER_CONTEXT=default docker compose up --build -d
```

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
