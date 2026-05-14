# 009 — Harden Local Startup And Bedrock Defaults

## Goal

Remove the setup errors encountered during direct local startup by fixing
Python package metadata, service config parsing, and Bedrock defaults/docs.

## Status

Done.

## Acceptance Criteria

- Python workspace members can be synced as installable packages for direct
  `uv run` service startup.
- News service accepts the documented `TAVILY_API_KEY` env var.
- Agent service defaults/docs point local Bedrock runs at an
  inference-profile-compatible Claude 4 ID.
- Startup docs and example env files match the real local and Docker paths.

## Related Docs

- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`
