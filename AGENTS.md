# AGENTS.md — Instructions for AI Coding Agents

## Project Overview

Rozbirnyk is a multi-agent system that produces political forecasts.

Inputs:
- news data
- social opinion data
- prediction markets (Polymarket)
- structured knowledge (documents/books)

Output:
- probability-based political forecasts

Architecture:
- apps:
  - agent_service — orchestration (FastAPI)
  - backend — core API logic
  - frontend — Streamlit UI
- mcp_servers:
  - knowledge_service
  - news_service
  - opinion_service
  - probability_service
- packages:
  - common — shared utilities (logging, helpers)
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
- FastAPI (backend services)
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
- Run service: `docker compose up agent-service`
- Lint/format/typecheck:
  `uv run pre-commit run --all-file`
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

This rule is critical for reducing context usage and improving efficiency.

---

## Code Style

- Line length: 88
- Formatting: Ruff
- Import sorting: Ruff (I rules)
- Typing: strict mypy, no `Any` unless unavoidable
- Async preferred in I/O and API layers
- Keep dependencies minimal and justified
- No print() in production code

---

## Comments

- Every file must start with a docstring describing purpose.
- Use docstrings for all documentation:
  - module: purpose
  - class: responsibility
  - function/method: behavior, inputs, outputs, edge cases
  - tests: what is being validated

- Code must be self-explanatory via naming and structure.

- Inline comments (`#`) are forbidden except:
  - TODOs
  - external constraints (API / legacy / system behavior)
  - rare cases where refactoring reduces clarity more than a short note

- If inline comments feel necessary, refactor first.

---

## Testing Rules

- All features and bug fixes must include tests
- No testless features allowed
- Use pytest + asyncio mode
- Tests must be deterministic (no real network/time dependency unless mocked)
- Target ≥80% coverage
- Place tests next to code

---

## Docker Rules

- Use existing multi-stage uv Docker pattern
- Build command must include:
  `uv sync --frozen --no-dev --no-editable`
- One service per container
- Do not modify base images without strong justification
- Never use privileged containers
- Never mount host root directories

---

## Git Rules

- Conventional commits only (feat, fix, refactor, chore)
- Always run tests + lint before commit
- Never push directly to main
- PR must describe what changed and why

---

## What NOT to do

- Do not add unnecessary dependencies
- Do not bypass linting or type checking
- Do not weaken logging or context propagation
- Do not use print() for debugging
- Do not commit secrets or environment files
- Do not modify docker-compose or infra without reason
- Do not touch cache/build artifacts

---

## Agent Behavior Rules

- Understand service responsibility before changing it
- Keep changes minimal and local unless explicitly required
- For cross-service changes, consider full pipeline impact:
  news → opinion → knowledge → probability → agent_service
- Prefer incremental improvements over large refactors
- Keep system observable at all times

---

## Decision Principle

When uncertain:
1. Prefer simplicity over abstraction
2. Prefer explicit code over clever code
3. Prefer local changes over global refactors
4. Prefer consistency over optimization