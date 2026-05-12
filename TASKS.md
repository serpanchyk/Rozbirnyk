# TASKS.md

## In Progress

None.

---

## Done Recently

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
