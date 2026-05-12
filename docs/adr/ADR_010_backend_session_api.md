# ADR 010: Backend Session API with SSE Progress Relay

## Status
Accepted

## Context
The browser UI should not talk directly to LangGraph internals, MCP endpoints,
or the wiki lifecycle API. Those surfaces expose system details the frontend
does not need and would force the browser to understand agent-service run
semantics, wiki resets, and event polling.

The current implemented slice of Rozbirnyk is a World Builder workflow. Users
need a stable application API that can:

1. create a new simulation session,
2. reset its wiki deterministically,
3. start one World Builder run for that session,
4. expose coarse run status and final file summaries, and
5. stream progress to the UI as simple server-sent events.

## Decision
We will keep `apps/backend` as the browser-facing application boundary and make
it responsible for session orchestration and progress relay.

### 1. In-Memory Session Records
The backend owns `SessionStore`, which keeps one `SessionRecord` per user
session in memory. Each record stores:

- `session_id`
- scenario text
- requested limits
- run status and stage
- latest `run_id`
- effective limits and terminal error, when available

This state is intentionally lightweight and mirrors upstream world-builder
status instead of persisting a second copy of wiki content.

### 2. Upstream Coordination
The backend coordinates two upstream services:

- `wiki_service` for deterministic `POST /api/v1/wiki/reset` and final file
  listing
- `agent_service` for starting runs and reading run status/events

The backend does not construct LangGraph state and does not discover MCP tools.
It remains an orchestration boundary.

### 3. Public API Shape
The backend exposes a narrow HTTP API:

- `POST /api/v1/sessions`
- `POST /api/v1/sessions/{session_id}/world-builder`
- `GET /api/v1/sessions/{session_id}`
- `GET /api/v1/sessions/{session_id}/events`

`GET /events` is the browser contract. It hides agent-service polling and emits
frontend-ready SSE events such as `world_builder.started` and
`world_builder.file_created`.

### 4. SSE Relay Model
The backend relays progress instead of proxying a raw upstream stream. It polls
agent-service event snapshots by `after_sequence`, formats each event as SSE,
and stops once a terminal event is observed.

This keeps the browser protocol simple and gives the backend one place to map
upstream failures into a UI-visible terminal event.

## Consequences

### Positive
- The frontend depends on one stable application API instead of multiple
  service-specific protocols.
- Wiki reset and run creation stay ordered in one service boundary.
- SSE payloads are typed around user-visible progress rather than internal
  agent-service objects.

### Negative
- Session and run tracking are currently process-local; a backend restart loses
  transient session metadata.
- The backend polls agent-service every 500 ms instead of using push-based
  upstream delivery.

### Mitigation
- Keep backend models narrow so a future persistent session store can replace
  the in-memory implementation without changing the public API.
- Treat the SSE relay as an application contract; the transport between backend
  and agent-service can change later without forcing frontend changes.
