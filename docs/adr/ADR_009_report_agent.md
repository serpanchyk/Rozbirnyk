# ADR 010: Post-Simulation Synthesis via the Report Agent

## Status
Accepted

## Context
Rozbirnyk is fundamentally a political forecasting tool. The Simulation Orchestrator (ADR 009) and the Actors generate a rigorous, chronologically accurate audit trail of events in `Timeline.md`, along with mutated `States/` and `Actors/` Markdown files. 

However, a raw log of validated agent actions is not a forecast; it is a database of events. Human decision-makers and users require a digestible, analytical narrative that explains *why* the simulated future unfolded the way it did, highlights key turning points, and directly answers the original "What if" query. We need a mechanism to translate raw simulation state into high-value intelligence.

## Decision
We will implement the **Report Agent** as an isolated, strictly read-only analytical pipeline that executes exclusively *after* the Simulation Orchestrator terminates the run.

### 1. Read-Only Constraint
The Report Agent operates with zero mutation privileges. It is denied access to all MCP tools that alter the Wiki (e.g., `edit_state_file`, `append_to_timeline`). It only utilizes:
*   `read_state_file`
*   `read_timeline`
*   `read_actor_file`

Before it begins reading full files, the Report Agent is injected through the Wiki API with the title and short description of every Wiki file. This lets it select relevant state and actor files without mutating or rediscovering the Wiki structure through MCP.

### 2. Structured Analytical Pipeline
The Agent does not simply summarize the text. It uses a structured prompt to evaluate the simulation data and produce a final `Forecast_Report.md` containing:
*   **Executive Summary:** A concise answer to the initial "What if" scenario.
*   **Key Turning Points:** Identification of the 2-3 most critical actions from the `Timeline.md` that irrevocably altered the trajectory of the simulation.
*   **Final State Assessment:** A breakdown of the newly established geopolitical, economic, or social reality.
*   **Actor Outcomes:** A summary of which entities achieved their goals and which failed.

### 3. Execution Handoff
Once the Orchestrator hits a termination condition (ADR 009), it signals the core `agent_service` API. The API then spins up the Report Agent, passes it the session ID/Trace ID, and waits for the final markdown report to serve to the Streamlit UI.

## Consequences

### Positive
*   **Clear Output Focus:** By separating the "playing" of the simulation from the "analysis" of the simulation, we ensure the final LLM call is entirely optimized for readability and strategic forecasting, rather than validation logic.
*   **Safety:** The hard read-only constraint guarantees the Report Agent cannot accidentally hallucinate new events into the official `Timeline.md` while trying to write its summary.
*   **Reprocessing:** Because the Report Agent is decoupled, a user can prompt the Report Agent multiple times on the *same* finished simulation to get different analytical angles (e.g., "Analyze this timeline strictly from an economic perspective" vs. "Analyze military movements").

### Negative
*   **Context Window Limitations:** For long-running simulations, the `Timeline.md` and combined final `States/` files will exceed a single LLM's context window, causing the Report Agent to suffer from "lost-in-the-middle" recall degradation.
*   **Cost:** Generating a massive, comprehensive report requires a high-token output phase at the very end of an already expensive simulation run.

### Mitigation
*   **Map-Reduce Summarization:** If the `Timeline.md` exceeds a designated token threshold (e.g., 60,000 tokens), the Report Agent will employ a Map-Reduce strategy: chunking the timeline into historical "epochs," summarizing each epoch individually, and then generating the final forecast from the epoch summaries.
