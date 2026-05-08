# AGENTS.md — Instructions for AI Coding Agents

## Project Overview

Rozbirnyk is an autonomous world-modeling engine that transforms "What if" queries into dynamic, multi-agent simulations grounded in real-world data.

Inputs:
- User "What if" scenarios
- Real-time news and contextual data (Tavily)

Output:
- Chronological simulation timeline (`Timeline.md`)
- Evolving Markdown-based World Wiki (States and Actors)
- Final narrative report of the simulated future

Architecture:
- apps:
  - simulation_engine — ReAct loops for Builder, Orchestrator, Actors, Report (LangGraph)
  - frontend — Streamlit UI or CLI
- mcp_servers:
  - news_service — Tavily ingestion and caching
  - wiki_service — File system I/O for State, Timeline, and Actor files
- packages:
  - common — shared utilities (logging, caching, helpers)
- infra:
  - logging/fluentd — log pipeline

Each service is an independent uv package with its own `pyproject.toml` and Dockerfile.

---

## Engineering Standard

All code must be:
- production-ready
- strongly typed
- minimal dependency footprint
- observable via structured logging
- async-first where appropriate

---

## Tech Stack

- Python 3.12+
- uv (workspace-based dependency management)
- LangGraph (Agent orchestration and state transitions)
- FastAPI (backend services/MCP transport)
- Streamlit (frontend)
- Docker (multi-stage builds using uv base image)
- Logging: JSON structured logs (trace_id, session_id, user_id)
- Linting: Ruff
- Type checking: mypy (strict)
- Testing: pytest + pytest-asyncio + coverage
- CI: GitHub Actions + pre-commit

---

## Project Structure Rule

- All code must live under `src/<package_name>/`
- No business logic outside `src/`
- No circular imports

---

## Development Commands

- Install/sync: `uv sync`
- Full install: `uv sync --all-extras`
- Run stack: `docker compose up --build`
- Run service: `docker compose up <service_name>`
- Lint/format/typecheck:
  `uv run pre-commit run --all-files`
- Tests: `uv run pytest`
- Lock deps: `uv lock`

Never use `pip install`.

---

## Command Execution Rules

When reading or working with command outputs (CLI, logs, CI results, test output):

- Always prioritize the **last part (tail)** of the output first.
- The most relevant information is typically at the end (errors, summaries, final states).
- Only read full output if the tail is insufficient to determine the issue or result.
- Prefer incremental narrowing instead of full re-reading of long outputs.
- Avoid reprocessing already-seen output unless new information is required.

---

## Code Style

- Line length: 88
- Formatting: Ruff
- Import sorting: Ruff (I rules)
- Typing: strict mypy, no `Any` unless unavoidable
- Async preferred in I/O and API layers
- Keep dependencies minimal and justified
- No print() in production code
- No magic numbers: All constants, ports, and settings must be defined in the service's `config.toml` and validated by its `schema.py`.

---

## Logging Rules

- `setup_logger` must be called only once, in the main entry point of a service (e.g., `main.py`).
- Do not call `setup_logger` in any other file.
- Use the configuration system to manage log levels.

---

## Documentation Structure & Rules

**Strict Update Rule:** If you make code changes that alter system behavior, architecture, or configuration, you **MUST** update the corresponding documentation files in the `docs/` directory to reflect these changes.

**Documentation Architecture (`docs/`):**
- `VISION.md`: The North Star. Defines high-level goals, core principles, non-goals, and the core simulation loop.
- `ARCHITECTURE.md`: Defines system components (agents, state layer), data flow, tool integration (MCP), and the tech stack.
- `adr/`: Architecture Decision Records. Contains individual `.md` files (e.g., `ADR_001.md`) documenting the context, decisions, and consequences of major engineering choices.

**Code Comments:**
- Every module, class, and public function must have a docstring. Private ones need it if logic is non-trivial.
- Use **Google-style docstrings** that explain intent and behavior, not implementation.
- Place documentation at the top of the file and inside every class, function, and method. 
- The first line must be a short imperative summary.
- Type hints must not be repeated in the docstring. Include `Args`, `Returns`, and `Raises` when relevant.
- Include examples for non-trivial logic.
- Avoid vague or outdated docs and remove docs that don’t improve understanding.
- For the system, explicitly document data flow, role in the simulation/forecasting, logging context (if relevant), and note async behavior when needed.
- Inline comments (`#`) are forbidden except:
  - TODOs
  - external constraints (API / legacy / system behavior)
  - rare cases where refactoring reduces clarity more than a short note.
  - If inline comments feel necessary, refactor first.

---

## Testing Rules

- All features and bug fixes must include tests.
- No testless features allowed.
- Use pytest + asyncio mode.
- Tests must be deterministic (no real network/time dependency unless mocked).
- Target ≥80% coverage.
- Place tests next to code.
- To check that tests pass you should run: `uv run pytest /path/to/test_file.py`

---

## Docker Rules

- Use existing multi-stage uv Docker pattern.
- Build command must include: `uv sync --frozen --no-dev --no-editable`
- One service per container.
- Do not modify base images without strong justification.
- Never use privileged containers.
- Never mount host root directories.

---

## Git Rules

- Conventional commits only (feat, fix, refactor, chore).
- Always run tests + lint before commit.
- Never push directly to main.
- PR must describe what changed and why.

---

## What NOT to do

- Do not add unnecessary dependencies.
- Do not bypass linting or type checking.
- Do not weaken logging or context propagation.
- Do not use print() for debugging.
- Do not commit secrets or environment files.
- Do not modify docker-compose or infra without reason.
- Do not touch cache/build artifacts.

---

## Agent Behavior Rules

- Understand service responsibility before changing it.
- Keep changes minimal and local unless explicitly required.
- For cross-service changes, consider full pipeline impact:
  news_service -> World Builder -> Wiki -> Orchestrator -> Actors -> Wiki -> Report Agent
- Prefer incremental improvements over large refactors.
- Keep system observable at all times.
- If you change something in the code, do not justify it by saying "it's a good practice." You must explain exactly why the change is important and how it improves the system.