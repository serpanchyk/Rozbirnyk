# 015 — Resolve Docker Compose Clean Startup

## Goal

Make the documented Docker startup flow reliable and short so local operators
can start the full stack cleanly with a small set of commands.

## Status

Done.

## Acceptance Criteria

- `docs/run-project.md` documents an idempotent default startup flow.
- Cleanup commands remain available, but only for explicit reset/recovery.
- `docker-compose.yaml` avoids fixed container names that can cause recreate
  conflicts.
- Related handoff docs reflect the new startup guidance.

## Related Docs

- `docs/run-project.md`
- `docs/problems/docker-compose-clean-startup.md`
- `PROJECT_CONTEXT.md`
- `AGENTS.md`
