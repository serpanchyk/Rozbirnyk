# World Builder Events Polling Noise

## Summary

The 2026-05-15 Docker run generated excessive polling against the World Builder
events endpoint. The logs show a tight loop repeatedly requesting the same
`after_sequence=2` cursor, which creates unnecessary load and makes the run
logs difficult to inspect.

## Current Status

Open as of 2026-05-15.

## Evidence

- `agent_service` logged
  `GET /api/v1/world-builder/sessions/.../events?after_sequence=2` 357 times in
  a single run.
- The same cursor value was requested repeatedly instead of advancing to later
  sequence numbers.
- The polling continued around the end of the run even after
  `World Builder run completed.` was logged at `2026-05-15T12:17:40Z`.

## Impact

- Creates avoidable request volume between frontend and backend.
- Adds significant log noise, which hides meaningful operational events.
- Suggests wasted client or server work while the UI waits for state changes.

## Likely Root Cause

- The frontend or backend polling loop is too aggressive.
- The client may not be backing off when no new events are available.
- Completion state may not immediately stop the polling loop.

## Ideas For Resolution

- Add adaptive backoff when the event cursor does not advance.
- Stop polling immediately once the run reaches a terminal state.
- Consider server-sent events or websocket delivery for run events instead of
  repeated short-interval polling.
- Reduce access-log verbosity for this hot endpoint if polling remains the
  transport.

## Follow-Up Work

- Measure the exact polling interval used by the frontend.
- Confirm whether duplicate requests originate from one browser tab or multiple
  concurrent consumers.
- Add an automated regression test around terminal-state polling shutdown.
