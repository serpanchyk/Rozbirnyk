# AGENTS.md — Instructions for AI Coding Agents

Rozbirnyk = autonomous world-modeling engine for "What if" simulations.

Input:
- hypothetical scenarios
- real-time news/context

Output:
- simulation timeline
- evolving world wiki
- final future report

Core pipeline:
`news_service -> Builder -> Wiki -> Orchestrator -> Actors -> Report`

---

## Architecture

Services:
- `simulation_engine` — LangGraph multi-agent loops
- `frontend` — Streamlit/CLI
- `news_service` — news ingestion/cache
- `wiki_service` — filesystem state/wiki management
- `common` — shared utilities

Rules:
- each service is an isolated uv package
- all code under `src/<package>`
- no business logic outside `src`
- no circular imports

---

## Engineering Rules

- async-first for I/O
- strict typing
- structured JSON logging
- minimal dependencies
- production-ready only
- use Docker Compose to run the project unless the user explicitly asks for a
  direct per-service local run

Never:
- use `print()`
- use `pip install`
- add unnecessary deps
- weaken typing/linting

---

## Docs Rules

If behavior/architecture/config changes:
- update relevant docs in @docs/
- update @PROJECT_CONTEXT.md
Other docs rules:
- don't forget to update tasks and problems if you done changes to any
- if it's a significant change, add a note to the relevant section in @VISION.md
- if we came to a significant idea, create the separate ADR in @docs/adr/
- if you're encountering a problem, check @docs/problems/ for an existing doc before writing a new one
---

## Git rules
- after making any change or ending any task, make the commit

## Testing

- every feature needs tests
- deterministic tests only
- use pytest + asyncio

Run:
`uv run pre-commit run --all-files`
`uv run pytest`

---

## Important Agent Rules

- understand service responsibility first
- preserve observability
- when starting the project, read @docs/run-project.md and prefer docker compose way
  clean reset or explicit container cleanup is needed
- when reading logs/CLI output, check the tail first
