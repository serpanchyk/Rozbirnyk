# Bedrock Throttling Regression

## Summary

World Builder completed in the 2026-05-15 Docker run, but `agent_service`
still hit repeated Bedrock throttling during model invocation. This is a
regression from the previously resolved rate-limit issue because the run now
depends on retries rather than steady-state provider pacing.

## Current Status

Open as of 2026-05-15.

## Evidence

- `agent_service` logged `Bedrock throttled model invocation; retrying.` 7
  times during one run.
- Throttling appeared across multiple timestamps from `2026-05-15T12:14:53Z`
  through `2026-05-15T12:17:25Z`.
- At least one retry escalated to `attempt: 2`, which confirms that one retry
  round was not sufficient to recover immediately.
- The affected model was
  `us.anthropic.claude-sonnet-4-20250514-v1:0` via `aws_bedrock`.

## Impact

- End-to-end run time becomes unpredictable.
- User-facing progress can appear stalled while retries back off.
- Provider pressure remains high enough that larger or concurrent runs may still
  fail even if this one eventually completed.

## Likely Root Cause

- Current pacing and retry settings are not conservative enough for the active
  Bedrock quota and workload shape.
- Runtime concurrency may still allow bursts that exceed the provider's short
  window limits.
- The previous fix was sufficient to avoid hard failure, but not sufficient to
  eliminate sustained throttling under current usage.

## Ideas For Resolution

- Inspect the active `MODEL__...` and runtime pacing values used in Docker for
  this run and compare them with the intended Bedrock-safe defaults.
- Lower effective concurrency for World Builder model calls.
- Increase minimum spacing between provider calls.
- Add a run-level metric or warning threshold that marks sustained throttling as
  degraded service, not just a transient retry detail.

## Follow-Up Work

- Capture and document the effective Bedrock runtime configuration from the
  container environment during startup.
- Reproduce the same scenario with debug-level provider pacing telemetry
  enabled.
- Define an acceptable retry budget for a healthy run and alert when it is
  exceeded.
