# TASKS.md

## In Progress

None.

---

## Done Recently

### 001 — Backend ↔ Agent Service World Builder Flow

Goal: Let the backend start a World Builder run through agent-service, stream progress to the UI, and return the built world snapshot.

Status: Done

Implementation notes:
- Added backend session endpoints and agent-service World Builder run endpoints.
- First implementation uses backend polling instead of SSE.
- Frontend includes a minimal Streamlit flow for scenario submission, status display, and file lists.
- Basic World Builder limits are wired through config, request overrides, prompts, and post-run validation.

Expected flow:
1. Frontend submits scenario to backend.
2. Backend creates a session.
3. Backend calls agent-service to start World Builder.
4. Agent-service runs World Builder.
5. Progress events are exposed to backend/UI.
6. Built world is returned from wiki-service metadata.

Acceptance criteria:
- Backend can create a simulation session.
- Backend can start a World Builder run.
- UI can display current World Builder stage.
- UI can display created actors and state files.
- World Builder respects max actor/state-file limits.

Related docs:
- `PROJECT_CONTEXT.md`
- `docs/adr/ADR_006_world_builder.md`
- `docs/adr/ADR_005_world_wiki.md`

---

## Backlog

### 002 — Add World Builder limits

Goal: Make World Builder aware of hard limits such as max actors and max state files.

Status: Done

Acceptance criteria:
- Limits are stored in typed config.
- Request-level limits cannot exceed configured hard limits.
- Prompt includes limits.
- Runtime checks enforce limits.

---

### 003 — Add progress event model

Goal: Standardize progress events emitted by agent-service.

Status: Done

Example events:
- `world_builder.started`
- `world_builder.researching`
- `world_builder.file_created`
- `world_builder.completed`
- `world_builder.failed`

---

### 004 — Add SSE endpoint for UI loading state

Goal: Let frontend subscribe to backend progress updates.

Status: Done

Suggested endpoint:
`GET /api/v1/sessions/{session_id}/events`

---

### 005 — Improve frontend UI beyond basic Streamlit defaults

Goal: Replace the current minimal/generic frontend presentation with a more intentional UI, potentially using a JavaScript-capable frontend approach where needed for richer interactions and styling.

Status: Done

Acceptance criteria:
- Frontend no longer feels like a default Streamlit prototype.
- UI has a clear visual direction and better loading/progress presentation.
- Scenario submission, session status, and created file lists remain supported.
- Chosen frontend approach is documented, including whether Streamlit is extended or replaced.

---

### 006 — Add `docs/run-project.md` startup guide

Goal: Create a single runbook that explains how to start all Rozbirnyk services for local development.

Status: Done

Acceptance criteria:
- `docs/run-project.md` exists.
- Document covers dependency sync and how to start the full stack.
- Document covers how to run individual services when needed.
- Document includes the main URLs/ports for frontend, backend, agent-service, news-service, and wiki-service.

---

## Backlog

None.

---

## Blocked

None.
