# Bedrock Rate Limits

## Summary

World Builder runs were failing during Bedrock `Converse` calls with
`ThrottlingException`. The fix keeps Bedrock on inference-profile-first
configuration, adds process-local request pacing and retry behavior in
`agent_service`, and surfaces a typed `provider_rate_limited` failure through
backend and frontend.

## Status

Resolved on 2026-05-14.

## Chosen Fix

- Keep `MODEL__MODEL_ID` inference-profile-first for Docker and production-like
  runs. Raw model IDs remain supported, but they are not the default guidance.
- Add `model.runtime` controls for Bedrock:
  `max_concurrency`, `min_seconds_between_calls`, `max_retries`,
  `retry_base_seconds`, and `retry_max_seconds`.
- Wrap provider invocation behind one process-local semaphore and pacing gate in
  `LLMService`, then retry throttling failures with bounded exponential backoff
  and jitter.
- Convert exhausted Bedrock throttling into typed
  `provider_rate_limited`/`aws_bedrock` error payloads.
- Preserve provider/model metadata in run status, backend session status, and
  failure SSE payloads so the frontend can render cleaner messaging.
- Show the active model/profile in the frontend status card.

## Notes

- Intelligent Prompt Routing was left out of this change and remains future
  optimization work only.
- The request gate is process-local to `agent_service`; no distributed
  cross-container coordination was added in this version.
- Docker Compose now forwards repo-root `MODEL__...` overrides into
  `agent-service`, so Bedrock pacing changes for container runs belong in the
  repo-root `.env`, not the service-local `.env`.
- Local defaults were raised to a more conservative baseline of a two-second
  minimum gap, ten retries, and a sixty-second maximum backoff, and
  `agent_service` now logs both the active Bedrock runtime settings and
  exhausted provider-throttling failures explicitly.
