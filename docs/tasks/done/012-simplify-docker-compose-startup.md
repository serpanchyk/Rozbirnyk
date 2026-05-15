# 012 — Simplify Docker Compose Startup

## Goal

Make Docker Compose the primary startup path with one shared `.env` file and
minimal commands while keeping direct per-service local runs available as a
secondary workflow.

## Status

Done.

## Acceptance Criteria

- Docker Compose no longer depends on service-local `.env` files intended for
  localhost development.
- Root `.env.example` contains the required Docker startup inputs, including
  `TAVILY_API_KEY`.
- Startup docs are Docker-first and show a minimal command sequence.
- Compose networking remains compatible with existing internal service hostname
  defaults.

## Related Docs

- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`
