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
- read @TASKS.md for current work and update
- after ending the task, make the commit

---

## Testing

- every feature needs tests
- deterministic tests only
- use pytest + asyncio

Run:
`uv run pre-commit run --all-files`
`uv run pytest`

---

## Important Agent Rules

- keep changes minimal/local
- understand service responsibility first
- prefer incremental changes over refactors
- preserve observability
- when reading logs/CLI output, check the tail first
