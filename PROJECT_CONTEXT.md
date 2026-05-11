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
  Streamlit, Docker, Redis, Ruff, mypy, pytest.
- Core principle: Keep simulation state auditable through Markdown world files
  and structured logs.

## Current Architecture

- `apps/agent_service`: agent orchestration, tool registry, LangGraph flow
- `apps/backend`: backend application boundary
- `apps/frontend`: Streamlit UI boundary
- `mcp_servers/news_service`: Tavily-backed research tools with caching
- `mcp_servers/wiki_service`: session wiki and timeline storage/API
- `packages/common`: shared config, caching, and structured logging
- `infra/logging/fluentd`: local log pipeline

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
- State model: Markdown timeline plus state and actor files per session

## Active Tasks

- Keep this section current.
- Record in-progress work, blockers, or near-term priorities as short bullets.
- Remove stale items instead of letting the list grow forever.

- No active tasks recorded yet.

## Recent Decisions / Notes

- Use this section for decisions that matter in handoff but do not justify a
  full ADR.
- Keep entries short and dated when possible.

- 2026-05-11: Created `PROJECT_CONTEXT.md` as the canonical short handoff file
  for cross-agent and cross-chat continuity.

## Open Questions / Risks

- Fill this section only with unresolved items that can change implementation
  direction.

- None recorded yet.

## Next Update Checklist

Update this file when any of the following changes:

- current priorities or active tasks
- implemented architecture or service responsibilities
- important constraints, blockers, or assumptions
- cross-chat handoff notes another agent would need immediately
