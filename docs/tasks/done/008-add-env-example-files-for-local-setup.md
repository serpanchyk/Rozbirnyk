# 008 — Add `.env.example` Files For Local Setup

## Goal

Make local setup explicit by providing copyable environment templates for the
repo root and each service.

## Status

Done.

## Acceptance Criteria

- `.env.example` exists at the repo root.
- Each service directory has a matching `.env.example` where local
  configuration is expected.
- `docs/run-project.md` explains which example files to copy and which values
  must be filled in manually.

## Related Docs

- `PROJECT_CONTEXT.md`
- `docs/run-project.md`
