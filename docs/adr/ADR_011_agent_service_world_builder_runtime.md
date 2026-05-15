# ADR 011: Agent-Service Run Manager for World Builder Execution

## Status
Accepted

## Context
`agent_service` now owns executable LangGraph workflows rather than only future
architecture placeholders. The current production path is the World Builder:
discover role-scoped MCP tools, invoke the configured LLM, track progress, and
return a bounded summary of created wiki files.

Running the graph inline inside an HTTP handler would couple request lifetime to
LLM latency, make progress reporting awkward, and provide no central place to
enforce run limits or session exclusivity.

## Decision
We will execute World Builder runs through an in-memory asynchronous
`WorldBuilderRunManager`.

### 1. Background Run Ownership
`POST /api/v1/world-builder/runs` creates a `RunRecord`, marks it queued, emits
an initial event, and starts an `asyncio` background task for the actual graph
execution.

Only one queued or running World Builder run is allowed per session at a time.

### 2. Deterministic Progress Model
The run manager emits typed progress events with monotonically increasing
sequence numbers. The current coarse stages are:

- `queued`
- `researching`
- `building_states`
- `building_actors`
- `collecting_snapshot`
- `completed`
- `failed`

After graph completion, agent-service fetches wiki file metadata through the
wiki HTTP API and emits file-created events from that deterministic snapshot
instead of relying on free-form model text.

### 3. Tool and Model Construction
Startup-time dependencies are built centrally:

- `LLMService` constructs the bindable chat model from typed config.
- `ToolRegistry.discover()` loads MCP tools from configured Wiki and News
  servers.
- `WorldBuilder` receives only its role-scoped tool set from the registry.

The HTTP API never exposes raw MCP tools to callers.

### 4. Tracing Boundary
When LangSmith tracing is enabled, the run manager attaches a runnable config
containing:

- `session_id`
- `run_id`
- `max_actors`
- `max_state_files`

Tracing is optional and limited to workflow execution in `agent_service`.

## Consequences

### Positive
- Long-running World Builder execution is decoupled from HTTP request lifetime.
- The run manager provides one authoritative place to enforce hard limits and
  emit frontend-visible progress.
- Deterministic file summaries make completion results less sensitive to model
  phrasing.

### Negative
- Run state is currently memory-resident and lost on service restart.
- Agent-service still exposes only the World Builder vertical slice; the
  Orchestrator, Actor, and Report Agent phases remain planned but unimplemented.

### Mitigation
- Keep the run-manager API explicit so persistent backing storage or a job queue
  can be introduced later.
- Document the implemented scope clearly in architecture docs to avoid implying
  that the full simulation loop already ships.
