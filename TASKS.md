# TASKS.md

## In Progress

None.

---

## Done Recently

### 013 — Harden Docker startup and local env parity

Goal: Make clean Docker Compose startup the default agent workflow, enable
LangSmith tracing for LangGraph runs, and align local environment files with
their examples.

Status: Done

Acceptance criteria:
- Agent and human startup docs run `docker compose down --remove-orphans`
  before rebuilding the stack.
- Agent rules default to Docker Compose startup unless the user says otherwise.
- Local ignored `.env` files contain the keys from their matching examples
  without exposing or replacing existing secrets.
- News service local config uses the documented `TAVILY_API_KEY` name.

Related docs:
- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `docs/run-project.md`

### 012 — Simplify Docker Compose startup

Goal: Make Docker Compose the primary startup path with one shared `.env` file
and minimal commands while keeping direct per-service local runs available as a
secondary workflow.

Status: Done

Acceptance criteria:
- Docker Compose no longer depends on service-local `.env` files intended for
  localhost development.
- Root `.env.example` contains the required Docker startup inputs, including
  `TAVILY_API_KEY`.
- Startup docs are Docker-first and show a minimal command sequence.
- Compose networking remains compatible with existing internal service hostname
  defaults.

Related docs:
- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`

### 011 — Refresh architecture documentation and diagrams

Goal: Bring ADRs, diagrams, and handoff docs in line with the current
backend/frontend/agent-service architecture and the implemented World Builder
runtime slice.

Status: Done

Acceptance criteria:
- ADR numbering is internally consistent.
- Missing architecture decisions are recorded for backend session orchestration,
  agent-service run management, and the React/Vite frontend.
- Mermaid diagrams describe the real current runtime path and clearly mark
  planned later phases.
- `README.md` and `PROJECT_CONTEXT.md` match the updated architecture story.

Related docs:
- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/adr/`
- `docs/diagrams/`

### 010 — Refresh frontend to white theme and add LangSmith tracing

Goal: Update the frontend visual direction to a white/light theme and add
LangSmith tracing for observability of agent and workflow runs.

Status: Done

Acceptance criteria:
- Frontend uses a deliberate white/light visual theme with white as the primary
  background and purple as the main accent color.
- Core screens remain readable and usable on desktop and mobile.
- LangSmith integration is wired through typed configuration and environment
  variables.
- Relevant simulation/agent workflow runs emit traces to LangSmith when
  configured.
- Setup and usage are documented for local development.

Related docs:
- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`

### 009 — Harden local startup and Bedrock defaults

Goal: Remove the setup errors encountered during direct local startup by fixing
Python package metadata, service config parsing, and Bedrock defaults/docs.

Status: Done

Acceptance criteria:
- Python workspace members can be synced as installable packages for direct
  `uv run` service startup.
- News service accepts the documented `TAVILY_API_KEY` env var.
- Agent service defaults/docs point local Bedrock runs at an
  inference-profile-compatible Claude 4 ID.
- Startup docs and example env files match the real local and Docker paths.

Related docs:
- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`

### 008 — Add `.env.example` files for local setup

Goal: Make local setup explicit by providing copyable environment templates for
the repo root and each service.

Status: Done

Acceptance criteria:
- `.env.example` exists at the repo root.
- Each service directory has a matching `.env.example` where local configuration
  is expected.
- `docs/run-project.md` explains which example files to copy and which values
  must be filled in manually.

Related docs:
- `PROJECT_CONTEXT.md`
- `docs/run-project.md`

### 007 — Remove local EFK observability stack

Goal: Simplify local development by removing Elasticsearch, Kibana, and Fluentd
from Docker Compose while preserving structured JSON logs.

Status: Done

Acceptance criteria:
- Docker Compose no longer defines Elasticsearch, Kibana, or Fluentd services.
- Application services still emit structured JSON logs.
- Startup and observability docs describe direct stdout or `docker compose logs`
  usage instead of Kibana-based inspection.

Related docs:
- `PROJECT_CONTEXT.md`
- `docs/adr/ADR_002_logging.md`
- `docs/run-project.md`

---

## Backlog

None.

---

## Blocked

None.
