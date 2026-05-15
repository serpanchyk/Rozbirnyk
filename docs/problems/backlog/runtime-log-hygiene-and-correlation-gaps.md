# Runtime Log Hygiene And Correlation Gaps

## Summary

The 2026-05-15 Docker run completed without crashes, but the logs expose two
observability problems: important structured records are missing correlation
fields, and at least one service emits non-production banner/update noise that
does not belong in operational logs.

## Current Status

Open as of 2026-05-15.

## Evidence

- Important `agent_service` records, including throttling warnings and the final
  `World Builder run completed.` message, had `trace_id: null`,
  `session_id: null`, and `user_id: null`.
- The completion record did not include a populated session identifier even
  though the run was tied to a concrete backend session.
- `news_service` logs included a FastMCP ASCII banner and an upgrade prompt:
  `Update available: 3.3.0` and `Run: pip install --upgrade fastmcp`.

## Impact

- Cross-service debugging is harder because the most important records cannot be
  joined reliably by session or trace.
- Log streams contain presentation noise that weakens structured logging and
  complicates automated parsing.
- Production investigations take longer because operators must infer run context
  from surrounding access logs instead of reading it directly from key events.

## Likely Root Cause

- Session and trace metadata are not consistently propagated into
  `agent_service` run-manager and provider log calls.
- Third-party service startup output is not being suppressed or redirected away
  from the main runtime log stream.

## Ideas For Resolution

- Make `session_id` and `trace_id` mandatory for run lifecycle logs.
- Ensure correlation metadata is attached before provider calls and completion
  events are emitted.
- Disable or suppress third-party startup banners and upgrade prompts in
  container runs.
- Separate structured application logs from third-party console output when full
  suppression is not possible.

## Follow-Up Work

- Trace the logging context path from backend session creation into
  `agent_service`.
- Add tests that assert non-null correlation metadata on run lifecycle logs.
- Document an explicit policy for production-safe third-party logging in Docker
  services.
