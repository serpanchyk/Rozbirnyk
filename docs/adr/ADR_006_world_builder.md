# ADR 007: Phased Initialization via the World Builder Agent

## Status
Accepted

## Context
Rozbirnyk requires a mechanism to translate a brief user prompt (e.g., "What if the European Union bans AI open-source models?") into a fully populated, multi-agent simulation environment. 

If we allow the Simulation Orchestrator or individual Actors to fetch their own real-world context dynamically during the simulation, it will result in conflicting realities and "hallucination cascades." Furthermore, Actors should not have the cognitive burden of designing the world they live in; their token capacity must be reserved for playing their role. We need a dedicated, logically isolated initialization phase to establish the "Ground Truth" before the simulation begins.

## Decision
We will implement the **World Builder Agent** as a distinct, single-purpose ReAct loop (via LangGraph) that executes exclusively before the Simulation Orchestrator takes control.

### 1. Responsibilities & Execution Flow
The World Builder is responsible for the "Genesis" phase of the simulation:
*   **Research:** It queries the `news_service` MCP (Tavily tools) to gather current real-world context related to the user's "What if" scenario.
*   **World Synthesis:** It generates the foundational `States/` files (e.g., current laws, economic baselines).
*   **Actor Synthesis:** It identifies the necessary entities (e.g., "EU Parliament," "Open Source Community," "Tech Megacorporations") and generates their `Actors/` character sheets (goals, policies, initial memory).
*   **Formatting Compliance:** It ensures all generated files strictly adhere to the Title + Short Description indexing rule established in ADR 005.

### 2. Strict Handoff (The Boundary)
The World Builder operates with broad "Write" access to the entire Wiki. However, once the Wiki is fully populated, the World Builder **terminates**. It does not participate in the simulation loop, does not read the `Timeline.md` as it evolves, and cannot alter the world state once the Actors begin their turns.

## Consequences

### Positive
*   **Single Source of Truth:** All Actors start the simulation with a synchronized, conflict-free view of reality, drastically reducing logical contradictions during execution.
*   **Cognitive Separation:** The complex logic of translating web searches into structured Markdown is isolated from the logic of simulating geopolitical actions.
*   **Modularity:** The "Genesis" phase can be bypassed entirely if a user wants to load a pre-existing, manually crafted Wiki directory to run a simulation without the builder.

### Negative
*   **High Initial Latency:** The simulation takes significant time to start, as the Builder must complete multiple ReAct cycles and external API calls before the Orchestrator can take its first turn.
*   **Builder Bias:** The entire trajectory of the simulation is highly dependent on the quality of the Builder's initial search queries and its synthesis of the actors. A poor initialization dooms the simulation.

### Mitigation
*   The Builder's system prompt will include strict constraints to limit the maximum number of generated actors and state files to prevent context bloat and excessive startup times.
*   We will leverage the Hybrid REST/MCP Architecture (ADR 006) to stream the Builder's progress to the frontend, providing UX feedback to the user while the world is being constructed.