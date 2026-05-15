# ADR 012: React/Vite Frontend for Live World Builder Progress

## Status
Accepted

## Context
The earlier Streamlit-oriented frontend assumptions no longer match the code.
Rozbirnyk now ships a browser UI in `apps/frontend` that submits scenarios to
the backend and displays live World Builder progress.

The current product slice is not a general wiki explorer yet. It is a focused
operator UI for launching a world build, monitoring progress, and inspecting the
resulting actor and state file summaries.

## Decision
We will use a React/Vite single-page frontend as the primary local UI.

### 1. Backend-Only Browser Dependency
The browser talks only to `apps/backend` over HTTP and SSE through
`VITE_BACKEND_URL`. It does not call `agent_service`, `wiki_service`, or MCP
servers directly.

### 2. Live Progress Contract
The UI creates a session, starts the World Builder, opens an `EventSource`
against `/api/v1/sessions/{session_id}/events`, and merges ordered session
events into the visible timeline.

Terminal events trigger a final backend refresh so the UI can display the
resulting `state_files` and `actor_files` snapshot.

### 3. Present-Scope UX
The current interface is intentionally narrow:

- scenario input
- per-run file-count limits
- coarse status and stage badges
- ordered progress timeline
- state-file and actor-file summary panels

The frontend does not yet render full markdown files, download session exports,
or execute later simulation phases.

## Consequences

### Positive
- The UI boundary is decoupled from Python service internals.
- SSE gives immediate operator feedback during long World Builder runs.
- The frontend can evolve independently from LangGraph and MCP implementation
  details as long as the backend contract remains stable.

### Negative
- Browser state is ephemeral; reloading loses the active in-page event list.
- The interface currently reflects only the World Builder slice, not the full
  target simulation/reporting experience.

### Mitigation
- Keep session/event models typed in both backend and frontend so later UI
  expansion reuses the same application contract.
- Document the current scope explicitly in repo diagrams and README text.
