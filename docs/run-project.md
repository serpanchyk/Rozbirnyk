# Run Rozbirnyk

This document is the canonical startup guide for Rozbirnyk in local development.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+ and `npm`
- Docker and Docker Compose for the full-stack path
- `TAVILY_API_KEY` for `news_service`
- AWS credentials for the Bedrock model used by `agent_service`

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

- `.env.example`: shared Docker Compose port and Redis defaults.
- `apps/backend/.env.example`: optional backend port and upstream overrides for local runs.
- `apps/agent_service/.env.example`: optional local MCP endpoint overrides and World Builder limits.
- `apps/frontend/.env.example`: frontend backend URL for Vite.
- `mcp_servers/news_service/.env.example`: required `TAVILY_API_KEY` plus optional service overrides.
- `mcp_servers/wiki_service/.env.example`: optional wiki service port, logging, and storage overrides.

Notes:

- Replace `TAVILY_API_KEY=replace-me` in `mcp_servers/news_service/.env`.
- AWS credentials for `agent_service` are still expected from normal AWS environment variables, shared profiles, or IAM roles; they are not loaded from these example files by the app config layer.
- For Docker Compose, the root `.env` and service `.env` files are read through `env_file`.
- For direct local service runs, the Python services read `.env` from their own working directory through `BaseServiceConfig`.

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
