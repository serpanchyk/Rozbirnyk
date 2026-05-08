# ADR 006: Hybrid API/MCP Architecture for Wiki Service

## Status
Accepted

## Context
In ADR 005, we established a file-based Markdown Wiki managed via the Model Context Protocol (MCP). However, treating MCP as the *exclusive* interface to the Wiki creates severe orchestration bottlenecks.

System-level operations—such as clearing the Wiki before a new simulation, initializing the directory structure, or serving the `Timeline.md` to the Streamlit frontend—do not require an LLM. Forcing the main `agent_service` or frontend to act as an MCP client for administrative tasks is an anti-pattern. We must separate the "Control Plane" (system administration) from the "Data Plane" (agent tool usage).

The Wiki also has a second responsibility: it must provide bounded, predictable context to agents before they call tools. Agents should not start each turn blind and repeatedly discover files through MCP calls. Instead, the API side of the Wiki provides file metadata and actor-specific file context as part of agent construction.

## Decision
We will architect the `wiki_service` as a hybrid FastAPI application exposing two distinct interfaces, backed by a shared core logic module.

### 1. API Side
Standard HTTP endpoints support system orchestration, UI integration, and deterministic agent context injection.
*   `POST /api/v1/wiki/reset`: Deletes and recreates the `States/`, `Actors/`, and `Timeline.md` structure.
*   `GET /api/v1/wiki/timeline`: Returns the parsed timeline for the Streamlit UI to render.
*   `GET /api/v1/wiki/export`: Zips the current Wiki state for downloading or saving scenarios.
*   `GET /api/v1/wiki/files`: Returns the title and short description of every Wiki file.
*   `GET /api/v1/wiki/actors/{actor_id}/files`: Returns the actor-specific files that must be injected into that Actor's runtime context.
All agents are initialized with the title and short description of all files in the Wiki. Actors are additionally initialized with their own actor files, because their identity, current state, goals, policies, and private memory are required before they can produce a grounded proposal.

### 2. Data Plane (MCP via Streamable HTTP)
The interface strictly for the LangGraph agents during the simulation loop.
*   `read_state_file`: Reads a complete state file.
*   `edit_state_file`: Replaces or updates a state file.
*   `read_timeline`: Reads `Timeline.md`.
*   `append_to_timeline`: Appends a validated event to `Timeline.md`.
*   `read_actor_file`: Reads a complete actor file.
*   `edit_actor_file`: Replaces or updates an actor file.
*   `append_to_actor_memory`: Appends an entry to an actor's private memory.
*   `delete_file`: Deletes one specific Wiki file except `Timeline.md`, which is never deleted through MCP.

The MCP tool surface is scoped per agent role by the `agent_service` Tool Registry. The registry maps internal capability IDs to concrete MCP tools, exposes stable model-facing names such as `wiki_read_state_file`, and injects system-controlled values such as `session_id` from LangGraph state instead of letting the model provide them.

| Agent | Allowed Wiki MCP Tools |
| --- | --- |
| World Builder | `read_state_file`, `edit_state_file`, `read_timeline`, `read_actor_file`, `edit_actor_file` |
| Simulation Orchestrator | `read_state_file`, `edit_state_file`, `read_timeline`, `append_to_timeline`, `read_actor_file`, `edit_actor_file`, `delete_file` |
| Actors | `read_state_file`, `read_timeline`, `append_to_actor_memory` |
| Report Agent | `read_state_file`, `read_timeline`, `read_actor_file` |

Agents have zero access to API-side lifecycle endpoints such as reset. API context injection is performed by application code before the agent loop starts; MCP is reserved for explicit tool use during reasoning.

## Consequences

### Positive
*   **Separation of Concerns:** Agents are restricted to participating in the simulation; application code maintains absolute control over the simulation lifecycle and context injection.
*   **UI Simplicity:** Streamlit can fetch the world state using simple `requests.get()` calls without needing a complex MCP client implementation.
*   **Safety:** Agents cannot discover lifecycle operations, and `Timeline.md` is protected from MCP deletion.
*   **Context Efficiency:** File titles and short descriptions give every agent a stable map of the Wiki before it decides which full files to read.

### Negative
*   **Increased Boilerplate:** The `wiki_service` requires defining both FastAPI routers and FastMCP tools, slightly increasing the codebase size.
*   **State Syncing:** We must ensure that a REST API call (like a reset) safely aborts or locks out any pending MCP tool calls from agents that are currently mid-loop.
*   **Permission Drift:** The Tool Registry must keep role profiles synchronized with the documented capability matrix.

### Mitigation
*   All file-system I/O logic will be abstracted into a core manager module. Both the API endpoints and the MCP tools will wrap these same core functions to ensure consistent error handling and file locking.
*   Role-specific MCP profiles are represented as explicit capability constants in the agent service, with tests that verify the World Builder receives only News research tools plus the Wiki tools listed in this ADR.
