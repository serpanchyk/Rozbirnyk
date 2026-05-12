# Rozbirnyk

Rozbirnyk is an autonomous world-modeling engine for exploring political,
economic, and social "What if?" scenarios. It turns a user prompt into a
grounded, multi-agent simulation backed by live contextual research, a persistent
Markdown world state, and a final narrative forecast.

The system is designed for possibility exploration, not deterministic prediction.
Its goal is to make plausible future trajectories auditable: the user should be
able to inspect what the model knew, which actors acted, which state changed, and
why the final report reached its conclusions.

## Core Idea

A simulation run follows four phases:

1. **Prompt:** The user provides a scenario, such as "What if a major country
   bans open-source AI models?"
2. **World building:** The World Builder researches current context through the
   News MCP service and creates the initial World Wiki.
3. **Simulation:** Actors propose actions from their goals and constraints. The
   Simulation Orchestrator validates those actions, mutates shared state, and
   appends official events to `Timeline.md`.
4. **Synthesis:** The Report Agent reads the final wiki and timeline, then
   produces a forecast report with key turning points and actor outcomes.

The project separates these responsibilities so that agents do not all fetch
their own conflicting context or mutate shared state independently.

Today, the implemented vertical slice stops after the World Builder phase. The
frontend, backend, agent-service, and wiki snapshot flow are live; the later
Simulation Orchestrator, Actor turn loop, and Report Agent remain documented
target architecture.

## Repository Layout

```text
.
├── apps/
│   ├── agent_service/      # LangGraph-facing orchestration and MCP integration
│   ├── backend/            # Backend application boundary
│   └── frontend/           # React/Vite user interface boundary
├── mcp_servers/
│   ├── news_service/       # Tavily-backed MCP tools for current research
│   └── wiki_service/       # Markdown World Wiki API and MCP tools
├── packages/
│   └── common/             # Shared config, cache, and structured logging utilities
├── docs/
│   ├── VISION.md           # Product and simulation vision
│   └── adr/                # Architecture decision records
├── docker-compose.yaml
├── pyproject.toml
└── uv.lock
```

Every service is an independent `uv` package with source code under
`src/<package_name>/`. Shared utilities live in `packages/common`.

## Main Components

### Agent Service

`apps/agent_service` owns agent-side integration. It discovers MCP tools,
adapts them for LangChain-compatible execution, and resolves role-scoped tool
profiles through a Tool Registry. The registry combines News and Wiki MCP tools,
exposes stable model-facing names, and injects system-controlled Wiki arguments
such as `session_id` from graph state.

The planned agent roles are:

| Role | Responsibility | Wiki access |
| --- | --- | --- |
| World Builder | Initialize state and actors from current research | Read/write state and actor files |
| Simulation Orchestrator | Validate actions and mutate the official world state | Read/write state, actors, and timeline; delete obsolete wiki files |
| Actor | Propose actions from a durable character sheet | Read state and timeline; append private memory |
| Report Agent | Produce the final forecast narrative | Read-only access to state, timeline, and actor files |

Only the World Builder execution path is implemented in `agent_service` today.
The remaining roles are defined as architecture and tool-policy targets.

### News Service

`mcp_servers/news_service` exposes Tavily-backed MCP tools:

- `search_recent_news`
- `search_deep_research`
- `extract_article_content`

Results are cached through Redis using the shared `common.cache` helpers. This
keeps repeated research calls cheaper and keeps a single simulation grounded in
a consistent view of external context.

### Wiki Service

`mcp_servers/wiki_service` manages the World Wiki. It has two interfaces backed
by the same filesystem manager:

- **HTTP API:** lifecycle and UI operations such as reset, timeline retrieval,
  file metadata, actor context, and session export.
- **MCP tools:** agent-facing reads and controlled writes during simulation.

Each session contains:

```text
<session_id>/
├── Timeline.md
├── States/
└── Actors/
```

`Timeline.md` is the official chronological event log. `States/` contains shared
world facts. `Actors/` contains character sheets with identity, current state,
goals, policies, and private memory.

### Common Package

`packages/common` provides:

- Pydantic/TOML configuration loading
- Redis-backed async caching helpers
- JSON structured logging with `trace_id`, `session_id`, and `user_id`
  context fields

## Technology Stack

- Python 3.12+
- `uv` workspaces
- FastAPI and FastMCP
- LangChain MCP adapters and LangGraph for orchestration loops
- AWS Bedrock via `langchain-aws` for production chat models
- Redis for tool-result caching
- React and Vite for the frontend boundary
- Docker Compose for local service orchestration
- Ruff, mypy, pytest, pytest-asyncio, and coverage

## Configuration

Non-sensitive service defaults live in each service's `config.toml`. Sensitive
values and environment-specific overrides belong in `.env` files and environment
variables.

For Docker Compose, the default startup path uses only the repo-root `.env`.
Compose reads that file for startup variables, but only the explicitly mapped
Docker settings are injected into containers. Service-local `.env` files are
reserved for direct per-service local runs.

Important configuration values:

| Service | Local config file | Default internal port |
| --- | --- | --- |
| Backend | `apps/backend/config.toml` | `8000` |
| Agent service | `apps/agent_service/config.toml` | `8001` |
| Frontend | `apps/frontend/.env` (`VITE_BACKEND_URL`) | `8501` |
| News service | `mcp_servers/news_service/config.toml` | `8000` |
| Wiki service | `mcp_servers/wiki_service/config.toml` | `8000` |

The News service requires a Tavily API key exposed as `TAVILY_API_KEY`.
The Agent service uses AWS Bedrock model settings in
`apps/agent_service/config.toml`; for Claude 4 models, prefer an inference
profile ID or ARN such as `us.anthropic.claude-sonnet-4-20250514-v1:0` instead
of the raw foundation model ID. AWS credentials should come from normal AWS
environment variables, shared profiles, or runtime IAM roles. Optional
LangSmith tracing lives under `observability.langsmith` in
`apps/agent_service/config.toml` and can be overridden with
`OBSERVABILITY__LANGSMITH__*` environment variables.

## Local Development

Install dependencies:

```bash
uv sync
```

Install all extras and development dependencies:

```bash
uv sync --all-extras
```

Prepare the shared Docker Compose environment:

```bash
cp .env.example .env
```

Set `TAVILY_API_KEY` in `.env` before starting the stack.

Run the complete local stack:

```bash
docker compose up --build
```

Detailed startup instructions for Docker and per-service local development live in
`docs/run-project.md`.

Run one service:

```bash
docker compose up wiki-service
```

Run the test suite:

```bash
uv run pytest
```

Run tests for one package:

```bash
uv run pytest mcp_servers/wiki_service/tests/wiki_service/test_wiki_manager.py
```

Run linting, formatting checks, and type checks through pre-commit:

```bash
uv run pre-commit run --all-files
```

Update the lockfile:

```bash
uv lock
```

Do not use `pip install`; dependency changes should go through `uv`.

## Docker Services

The Compose stack includes:

| Container | Purpose | Host port |
| --- | --- | --- |
| `rozbirnyk-frontend` | UI boundary | `8501` |
| `rozbirnyk-backend` | Backend boundary | `8000` |
| `rozbirnyk-agent` | Agent orchestration service | `8001` |
| `rozbirnyk-news` | Tavily MCP service | `8002` |
| `rozbirnyk-wiki` | Wiki API and MCP service | `8003` |
| `rozbirnyk-redis` | Cache store | `6379` |

Wiki session files are stored in the `wiki-data` Docker volume.

## Observability

Services use structured JSON logging. The common logger injects contextual fields
from `contextvars`:

- `trace_id`
- `session_id`
- `user_id`

`agent_service` can also emit optional LangSmith traces for World Builder
workflow runs. When enabled, each trace carries `session_id`, `run_id`, and the
effective actor/state-file limits so workflow execution can be correlated with
service logs.

In Docker Compose, inspect service logs directly with `docker compose logs` or
via the stdout/stderr stream of locally started services.

## Documentation

Start with:

- `docs/VISION.md` for the product vision and simulation loop
- `docs/adr/ADR_001_news_service.md` for grounded data ingestion
- `docs/adr/ADR_002_logging.md` for structured logging
- `docs/adr/ADR_003_config.md` for configuration rules
- `docs/adr/ADR_004_caching.md` for Redis caching
- `docs/adr/ADR_005_world_wiki.md` for Wiki service architecture
- `docs/adr/ADR_006_world_builder.md` for the World Builder phase
- `docs/adr/ADR_007_actors.md` for actor character sheets
- `docs/adr/ADR_008_simulation_orchestrator.md` for centralized validation
- `docs/adr/ADR_009_report_agent.md` for final report synthesis
- `docs/adr/ADR_010_backend_session_api.md` for backend session orchestration
- `docs/adr/ADR_011_agent_service_world_builder_runtime.md` for run management
- `docs/adr/ADR_012_frontend_live_progress_ui.md` for the browser UI contract

When code changes alter behavior, architecture, or configuration, update the
corresponding files in `docs/`.

## Development Standards

- Keep business logic under `src/<package_name>/`.
- Prefer async code for I/O and service boundaries.
- Keep dependencies minimal and explicit.
- Add tests for features and bug fixes.
- Maintain strict mypy compatibility.
- Use Ruff formatting and import sorting.
- Keep logs structured; do not use `print()` in production code.
- Store constants, ports, and service settings in `config.toml` and validate
  them through service schemas.

## Project Status

The repository currently contains the workspace, common infrastructure, News MCP
service, Wiki API/MCP service, Docker stack, tests for shared utilities and MCP
services, and the MCP tool-management foundation in the Agent service. The full
LangGraph simulation loops and end-user workflow are defined by the ADRs and are
being implemented incrementally.
