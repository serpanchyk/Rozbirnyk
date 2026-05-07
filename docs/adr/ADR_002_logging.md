# ADR 002: Context-Aware Structured JSON Logging via EFK Stack

## Status
Accepted

## Context
Rozbirnyk is a distributed, multi-agent system comprising FastAPI backends, MCP servers, and asynchronous ReAct loops. A single user query triggers concurrent, cross-service interactions. 

Using standard text logs or `print()` statements makes it impossible to trace the lifecycle of a specific simulation run across service boundaries. Furthermore, generating structured JSON logs via the `common.logging` package is only half the solution; we require a robust infrastructure pipeline to ingest, parse, index, and visualize these distributed logs locally without overwhelming the host machine.

## Decision
We will implement a unified, context-aware structured JSON logging system utilizing Python's `contextvars` and the **EFK (Elasticsearch, Fluentd, Kibana) stack** via Docker Compose.

### 1. Application-Level Logging (Producer)
*   **Context Propagation:** We use `contextvars` to implicitly manage request-scoped data (`trace_id`, `session_id`, `user_id`). This natively supports `asyncio` and ensures context flows through the call stack.
*   **Structured Output:** A centralized `ContextualJsonFormatter` in the `common` package forces all output to stdout as structured JSON.

### 2. Infrastructure Pipeline (Consumer)
*   **Fluentd (Aggregator):** Acts as the log forwarder (port `24224`). It is configured via `fluent.conf` to explicitly parse the incoming Docker logs as JSON, ensuring fields like `trace_id` are extracted as top-level indexed fields, not stringified text.
*   **Elasticsearch (Storage):** Operates as a single-node cluster (port `9200`) with X-Pack security disabled for local development friction reduction. It uses a constrained memory profile (`-Xms1g -Xmx1g`) to balance performance with local resource limits.
*   **Kibana (Visualization):** Provides the UI (port `5601`) for querying the indexed logs. 

## Consequences

### Positive
*   **Distributed Tracing:** Logs from the `news_service`, `wiki_service`, and `agent_service` can be seamlessly queried and correlated in Kibana using a single `trace_id`.
*   **Clean Signatures:** Business logic functions do not need to accept `trace_id` as parameters; the formatter handles injection.
*   **Health-Checked Startup:** The Docker Compose infrastructure uses strict dependency health checks, ensuring the logging pipeline is fully operational before application services attempt to connect.

### Negative
*   **Resource Intensity:** Running Elasticsearch and Kibana locally consumes significant RAM (minimum ~1.5GB combined) and CPU, which can strain local development environments.
*   **Human Readability:** Raw JSON logs in standard `docker logs` are harder to read directly in the terminal, forcing reliance on the Kibana UI for debugging.

### Mitigation
*   Elasticsearch JVM options are strictly capped at 1GB.
*   Local development without the full EFK stack remains possible by piping standard `docker logs` through CLI tools like `jq` to format the JSON for terminal readability.