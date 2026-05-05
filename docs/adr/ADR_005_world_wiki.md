# ADR 006: Hybrid REST/MCP Architecture for Wiki Service

## Status
Accepted

## Context
In ADR 005, we established a file-based Markdown Wiki managed via the Model Context Protocol (MCP). However, treating MCP as the *exclusive* interface to the Wiki creates severe orchestration bottlenecks. 

System-level operations—such as clearing the Wiki before a new simulation, initializing the directory structure, or serving the `Timeline.md` to the Streamlit frontend—do not require an LLM. Forcing the main `agent_service` or frontend to act as an MCP client for administrative tasks is an anti-pattern. We must separate the "Control Plane" (system administration) from the "Data Plane" (agent tool usage).

## Decision
We will architect the `wiki_service` as a hybrid FastAPI application exposing two distinct interfaces, backed by a shared core logic module.

### 1. Control Plane (REST API)
Standard HTTP endpoints for system orchestration and UI integration.
*   `POST /api/v1/wiki/reset`: Deletes and recreates the `States/`, `Actors/`, and `Timeline.md` structure.
*   `GET /api/v1/wiki/timeline`: Returns the parsed timeline for the Streamlit UI to render.
*   `GET /api/v1/wiki/export`: Zips the current Wiki state for downloading or saving scenarios.

### 2. Data Plane (MCP via SSE)
The interface strictly for the LangGraph agents during the simulation loop.
*   `read_state_file`, `edit_state_file`, `append_to_timeline`, etc.
*   Agents have zero access to the Control Plane (e.g., an agent cannot accidentally call the reset endpoint).

## Consequences

### Positive
*   **Separation of Concerns:** Agents are restricted to participating in the simulation; the Orchestrator maintains absolute control over the simulation lifecycle.
*   **UI Simplicity:** Streamlit can fetch the world state using simple `requests.get()` calls without needing a complex MCP client implementation.
*   **Safety:** We completely eliminate the risk of a hallucinating agent discovering and triggering a "wipe database" tool.

### Negative
*   **Increased Boilerplate:** The `wiki_service` requires defining both FastAPI routers and FastMCP tools, slightly increasing the codebase size.
*   **State Syncing:** We must ensure that a REST API call (like a reset) safely aborts or locks out any pending MCP tool calls from agents that are currently mid-loop.

### Mitigation
*   All file-system I/O logic will be abstracted into a core `wiki_manager.py` module. Both the REST endpoints and the MCP tools will wrap these same core functions to ensure consistent error handling and file locking.