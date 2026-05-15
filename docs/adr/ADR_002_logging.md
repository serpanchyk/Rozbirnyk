# ADR 002: Context-Aware Structured JSON Logging to Standard Output

## Status
Accepted

## Context
Rozbirnyk is a distributed, multi-agent system comprising FastAPI backends, MCP servers, and asynchronous ReAct loops. A single user query triggers concurrent, cross-service interactions. 

Using standard text logs or `print()` statements makes it impossible to trace the lifecycle of a specific simulation run across service boundaries. We need a consistent log shape that works both in Docker Compose and when services are run directly during development, without adding heavy local infrastructure that is unrelated to the core simulation workflow.

## Decision
We will implement a unified, context-aware structured JSON logging system using Python's `contextvars` and direct JSON emission to stdout/stderr.

### 1. Application-Level Logging (Producer)
*   **Context Propagation:** We use `contextvars` to implicitly manage request-scoped data (`trace_id`, `session_id`, `user_id`). This natively supports `asyncio` and ensures context flows through the call stack.
*   **Structured Output:** A centralized `ContextualJsonFormatter` in the `common` package forces all output to stdout as structured JSON.
### 2. Runtime Consumption
*   **Container-Friendly Output:** Docker Compose preserves the JSON log lines, so operators can inspect them with `docker compose logs` without any extra forwarding layer.
*   **Local-Process Parity:** The same log shape is emitted when a service is started with `uv run`, so local debugging and Compose debugging use the same observability model.

## Consequences

### Positive
*   **Distributed Tracing:** Logs from the `news_service`, `wiki_service`, and `agent_service` share a single `trace_id`, making cross-service correlation straightforward in terminal tools or downstream collectors.
*   **Clean Signatures:** Business logic functions do not need to accept `trace_id` as parameters; the formatter handles injection.
*   **Lower Friction:** Local startup does not depend on Elasticsearch, Kibana, or Fluentd being installed, healthy, or resource-available.

### Negative
*   **No Built-In UI:** Local development loses a bundled log search dashboard.
*   **Human Readability:** Raw JSON logs in standard terminal output are less convenient than a dedicated visualization tool.

### Mitigation
*   Developers can pipe `docker compose logs` or direct process output through CLI tools like `jq` for readability.
*   Production or hosted environments can still ship the same JSON logs into an external collector if deeper indexing or dashboards are required.
