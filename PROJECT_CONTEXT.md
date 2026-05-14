# PROJECT_CONTEXT.md

## Purpose

This file is the shortest reliable handoff for Rozbirnyk. Use it to brief a new
agent or chat on what the project is, what matters now, and what should happen
next.

## Project Snapshot

- Name: Rozbirnyk
- Goal: Turn "What if" prompts into grounded multi-agent simulations with a
  world wiki, chronological timeline, and final report.
- Primary stack: Python 3.12+, uv workspaces, FastAPI/FastMCP, LangGraph,
  React/Vite, Docker, Redis, Ruff, mypy, pytest.
- Core principle: Keep simulation state auditable through Markdown world files
  and structured logs.

## Current Architecture

- `apps/agent_service`: agent orchestration, tool registry, LangGraph flow
- `apps/backend`: backend application boundary
- `apps/frontend`: React/Vite UI boundary
- `mcp_servers/news_service`: Tavily-backed research tools with caching
- `mcp_servers/wiki_service`: session wiki and timeline storage/API
- `packages/common`: shared config, caching, and structured logging
## Canonical Docs

- Product vision: `docs/VISION.md`
- Repo overview: `README.md`
- Architecture decisions: `docs/adr/`
- Agent rules: `AGENTS.md`

## Working Rules

- All code lives under `src/<package_name>/`.
- Keep services strongly typed, observable, and async-first where appropriate.
- Use `uv`, never `pip install`.
- Features and fixes require tests.
- If behavior, architecture, or configuration changes, update `docs/`.
- If project context, priorities, or implementation status changes, update this
  file in the same task.

## Current Status

- Phase: Foundation and architecture implementation
- Repo shape: Multi-package workspace with app, MCP server, common package, and
  infra boundaries already defined
- Simulation model: World Builder -> Orchestrator -> Actors -> Report Agent
- Implemented runtime slice: Frontend -> Backend -> World Builder -> Wiki
- State model: Markdown timeline plus state and actor files per session

## Active Tasks

- Keep this section current.
- Record in-progress work, blockers, or near-term priorities as short bullets.
- Remove stale items instead of letting the list grow forever.

- No active tasks recorded.

## Recent Decisions / Notes

- Use this section for decisions that matter in handoff but do not justify a
  full ADR.
- Keep entries short and dated when possible.

- 2026-05-11: Created `PROJECT_CONTEXT.md` as the canonical short handoff file
  for cross-agent and cross-chat continuity.
- 2026-05-11: World Builder flow now exposes typed progress events in
  agent-service, backend streams them over SSE, and the frontend consumes live
  updates through a React/Vite UI on port `8501`.
- 2026-05-11: The old Streamlit frontend has been replaced by a JavaScript
  frontend in `apps/frontend`.
- 2026-05-11: Added `docs/run-project.md` as the canonical local startup guide
  for Docker and per-service development commands.
- 2026-05-11: News service defaults now align on SSE transport at internal port
  `8000`, and Docker Compose health checks/port mappings were corrected for the
  live stack.
- 2026-05-12: Removed the local Elasticsearch, Kibana, and Fluentd stack from
  Docker Compose; local observability now relies on structured JSON logs written
  directly to stdout/stderr.
- 2026-05-12: Added `.env.example` files for the repo root and each service so
  local setup has explicit, copyable environment templates.
- 2026-05-12: Local startup was hardened by packaging each Python workspace
  member for clean `uv run` imports, flattening news-service Tavily config back
  to `TAVILY_API_KEY`, and switching the default Bedrock Claude 4 setting to an
  inference-profile-compatible ID.
- 2026-05-12: Frontend now uses a white-first theme with purple accents, and
  `agent_service` can emit optional LangSmith traces for World Builder runs via
  typed config, `.env` overrides, and per-run metadata.
- 2026-05-12: Architecture docs were refreshed to reflect the current deployed
  slice, adding ADRs for backend session orchestration, agent-service run
  management, and the React/Vite frontend while updating Mermaid diagrams.
- 2026-05-12: Docker Compose startup was simplified to one repo-root `.env`
  plus `docker compose up --build`; service-local `.env` files are now treated
  as direct local-run overrides only, and Compose declares underscore network
  aliases to match existing internal service hostnames.
- 2026-05-12: Docker Compose now consumes documented host-port variables,
  fails fast when `TAVILY_API_KEY` is missing, and supports Bedrock auth through
  either standard AWS environment variables or a read-only mounted shared AWS
  credentials directory for `AWS_PROFILE`.
- 2026-05-14: Project startup policy now defaults agents to Docker Compose and
  runs `docker compose down --remove-orphans` before rebuilding the stack.
  Local ignored `.env` files were synchronized with examples, LangSmith tracing
  was enabled for LangGraph runs, and news-service config now supports the
  documented nested service env overrides alongside flat `TAVILY_API_KEY`.
- 2026-05-14: Added `docs/problems/` to track known operational issues as
  individual Markdown records, starting with Bedrock throttling failures
  during World Builder runs and Docker Compose clean-startup reconciliation
  failures caused by container stop/name-conflict problems.
- 2026-05-14: Replaced the single `TASKS.md` file with `docs/tasks/`,
  organized by status with one Markdown file per tracked task.
- 2026-05-14: Docker startup guidance now defaults to idempotent
  `docker compose up --build -d` instead of forcing `down` before each start,
  and `docker-compose.yaml` no longer pins explicit `container_name` values so
  Compose can recreate services without hard container-name conflicts.
- 2026-05-14: Bedrock-backed World Builder calls now run through a shared
  process-local semaphore and pacing gate, retry throttling with bounded
  exponential backoff, and surface typed `provider_rate_limited` errors plus
  active model/profile metadata through agent-service, backend, and frontend.
- 2026-05-14: Docker Compose now forwards repo-root `MODEL__...` overrides into
  `agent-service`, Bedrock pacing defaults were raised to a more conservative
  baseline, and `agent-service` logs now record the active Bedrock runtime
  settings plus structured provider-throttling failures.

## Open Questions / Risks

- Fill this section only with unresolved items that can change implementation
  direction.

- Agent-service and backend session/run tracking are currently in-memory only;
  service restarts lose transient progress state.
- Docker Compose clean restart is not yet fully reliable in the local
  environment because daemon-level container stop failures can leave stale
  `Created` containers behind.

## Next Update Checklist

Update this file when any of the following changes:

- current priorities or active tasks
- implemented architecture or service responsibilities
- important constraints, blockers, or assumptions
- cross-chat handoff notes another agent would need immediately
