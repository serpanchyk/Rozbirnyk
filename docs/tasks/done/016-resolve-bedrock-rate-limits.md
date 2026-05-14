# 016 — Resolve Bedrock Rate Limits

## Goal

Reduce avoidable Bedrock throttling failures in World Builder runs and expose
provider-capacity failures as typed, user-friendly runtime state instead of raw
exception text.

## Status

Done.

## Acceptance Criteria

- `agent_service` uses inference-profile-first Bedrock defaults plus
  configurable request semaphore, pacing, and retry controls.
- Bedrock throttling failures become structured `provider_rate_limited` errors
  with retryability metadata.
- Backend and frontend preserve typed error/model metadata through polling and
  SSE without changing event names.
- The UI shows the active model/profile and renders cleaner Bedrock
  rate-limit messaging.
- Startup docs describe inference-profile-first Bedrock setup and the new
  runtime controls.

## Related Docs

- `PROJECT_CONTEXT.md`
- `README.md`
- `docs/run-project.md`
- `docs/problems/resolved/bedrock-rate-limits.md`
