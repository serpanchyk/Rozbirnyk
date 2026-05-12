# Run Rozbirnyk

This document is the canonical startup guide for Rozbirnyk in local development.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+ and `npm`
- Docker and Docker Compose for the full-stack path
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

## Configure Environment Files

Copy the example files before running the stack:

```bash
cp .env.example .env
cp apps/backend/.env.example apps/backend/.env
cp apps/agent_service/.env.example apps/agent_service/.env
cp apps/frontend/.env.example apps/frontend/.env
cp mcp_servers/news_service/.env.example mcp_servers/news_service/.env
cp mcp_servers/wiki_service/.env.example mcp_servers/wiki_service/.env
```

What each file is for:

- `.env.example`: shared Docker Compose environment such as Redis defaults and
  optional AWS profile pass-through.
- `apps/backend/.env.example`: optional backend port and upstream overrides for local runs.
- `apps/agent_service/.env.example`: optional local MCP endpoint overrides and World Builder limits.
- `apps/frontend/.env.example`: frontend backend URL for Vite.
- `mcp_servers/news_service/.env.example`: required `TAVILY_API_KEY` plus optional service overrides.
- `mcp_servers/wiki_service/.env.example`: optional wiki service port, logging, and storage overrides.

Notes:

- Replace `TAVILY_API_KEY=replace-me` in `mcp_servers/news_service/.env`.
- AWS credentials for `agent_service` are still expected from normal AWS environment variables, shared profiles, or IAM roles; they are not loaded from these example files by the app config layer.
- For Docker Compose, the root `.env` and each service `.env` file explicitly
  listed under `env_file` in `docker-compose.yaml` are loaded into that
  container.
- For direct local service runs, the Python services read `.env` from their own working directory through `BaseServiceConfig`.

## Configure Amazon Bedrock Access

`agent_service` uses AWS Bedrock through the normal AWS credential provider
chain. Do not put AWS secrets into the repo `.env` files.

Supported local approaches:

- Use `aws configure` and the default shared profile.
- Use a named shared profile and export `AWS_PROFILE=<profile-name>`.
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
- If using Docker Compose, export `AWS_PROFILE` or AWS credential variables in
  the shell before `docker compose up --build` so Compose can pass them through
  from the environment or from service-level env files you control outside the
  repo.

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

## Run Services Locally

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
