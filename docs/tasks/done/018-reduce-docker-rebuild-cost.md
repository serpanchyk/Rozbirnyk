# 018 — Reduce Docker Rebuild Cost

## Goal

Reduce unnecessary Docker rebuild time during normal local development.

## Status

Done.

## Acceptance Criteria

- Unrelated repo changes do not invalidate every Python service dependency
  install layer.
- Python image builds reuse cached `uv` downloads when possible.
- Frontend image builds reuse cached npm downloads when possible.
- Startup docs explain the new build-cache behavior.

## Related Docs

- `PROJECT_CONTEXT.md`
- `docs/run-project.md`
- `docs/problems/resolved/docker-build-slow-rebuilds.md`
