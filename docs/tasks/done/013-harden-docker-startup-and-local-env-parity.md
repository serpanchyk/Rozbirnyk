# 013 — Harden Docker Startup And Local Env Parity

## Goal

Make clean Docker Compose startup the default agent workflow, enable LangSmith
tracing for LangGraph runs, and align local environment files with their
examples.

## Status

Done.

## Acceptance Criteria

- Agent and human startup docs run `docker compose down --remove-orphans`
  before rebuilding the stack.
- Agent rules default to Docker Compose startup unless the user says
  otherwise.
- Local ignored `.env` files contain the keys from their matching examples
  without exposing or replacing existing secrets.
- News service local config uses the documented `TAVILY_API_KEY` name.

## Related Docs

- `AGENTS.md`
- `PROJECT_CONTEXT.md`
- `docs/run-project.md`
