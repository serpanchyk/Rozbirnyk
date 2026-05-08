# ADR 007: Phased Initialization via the World Builder Agent

## Status
Accepted, amended 2026-05-08

## Context
Rozbirnyk requires a mechanism to translate a brief user prompt (e.g., "What if the European Union bans AI open-source models?") into a fully populated, multi-agent simulation environment. 

If we allow the Simulation Orchestrator or individual Actors to fetch their own real-world context dynamically during the simulation, it will result in conflicting realities and "hallucination cascades." Furthermore, Actors should not have the cognitive burden of designing the world they live in; their token capacity must be reserved for playing their role. We need a dedicated, logically isolated initialization phase to establish the "Ground Truth" before the simulation begins.

## Decision
We will implement the **World Builder Agent** as a distinct, single-purpose ReAct loop (via LangGraph `StateGraph` and `ToolNode`) that executes exclusively before the Simulation Orchestrator takes control. The implementation is owned by one `WorldBuilder` class. Graph construction, initial state creation, model invocation, prompt assembly, and routing all live on that class so the agent's lifecycle is easy to inspect in one place.

`WorldBuilder` inherits from the shared `AgentBase`, which centralizes role identity, role-scoped tool resolution, model tool binding, and the maximum-step setting. Future concrete agents, including the Simulation Orchestrator, Actors, and Report Agent, should inherit from `AgentBase` rather than recreating model/tool wiring.

Agent-service code is organized around shared runtime concerns:
*   Concrete agent classes and their LangGraph definitions live in `agent_service/agents/`.
*   Agent prompts live in `agent_service/prompts/`.
*   LangGraph state schemas live in `agent_service/schemas/`.
*   Agent service configuration remains in `agent_service/schema.py`.
*   External runtime services, including provider-independent LLM model management, live in `agent_service/services/`.
*   Tool resolution is split across `agent_service/tools/roles.py`, `bindings.py`, `discovery.py`, `wrappers.py`, and a thin `registry.py` coordinator so role policy, MCP discovery, and model-facing tool adaptation stay independently testable.

### 1. Responsibilities & Execution Flow
The World Builder is responsible for the "Genesis" phase of the simulation:
*   **Research:** It queries the `news_service` MCP (Tavily tools) to gather current real-world context related to the user's "What if" scenario.
*   **World Synthesis:** It generates the foundational `States/` files (e.g., current laws, economic baselines).
*   **Actor Synthesis:** It identifies the necessary entities (e.g., "EU Parliament," "Open Source Community," "Tech Megacorporations") and generates their `Actors/` character sheets (goals, policies, initial memory).
*   **Formatting Compliance:** It ensures all generated files strictly adhere to the Title + Short Description indexing rule established in ADR 005.

### 2. Strict Handoff (The Boundary)
The World Builder receives its tools through the `agent_service` Tool Registry. Its role profile combines current-context News capabilities (`search_recent_news`, `search_deep_research`, and `extract_article_content`) with only the Wiki MCP tools needed to initialize state and actor files: `read_state_file`, `edit_state_file`, `read_timeline`, `read_actor_file`, and `edit_actor_file`. It cannot append official events to `Timeline.md`, cannot append actor memory entries as a simulation participant, and cannot delete files.

The registry exposes stable model-facing names such as `news_search_recent_news` and `wiki_edit_state_file`. For Wiki tools, `session_id` is injected from LangGraph state and is not exposed as a model-controlled argument.

Role profiles and capability bindings are validated by the Tool Registry before tools are resolved. If a role references a capability without a binding, the registry raises a configuration error that names the role capability instead of surfacing a lower-level dictionary lookup failure. MCP discovery errors are also wrapped with the failing server name so startup failures distinguish `news_service` from `wiki_service`.

### 3. Model Runtime
The production model path is created through `LLMService`, which hides provider-specific model construction from agents. The initial provider is AWS Bedrock via `ChatBedrockConverse`. `agent_service/config.toml` stores non-sensitive defaults for `provider`, `model_id`, required `region_name`, `temperature`, and `max_tokens`; credentials remain in the standard AWS environment, profile, or IAM role chain. Agents receive the active bindable model object and do not know which provider or model-switching path produced it.

Tests pass fake models and fake tools directly into the graph factory so no AWS or live MCP service calls are made during unit tests.

Once the Wiki is fully populated, the World Builder **terminates**. It does not participate in the simulation loop, does not read the `Timeline.md` as it evolves, and cannot alter the world state once the Actors begin their turns.

## Consequences

### Positive
*   **Single Source of Truth:** All Actors start the simulation with a synchronized, conflict-free view of reality, drastically reducing logical contradictions during execution.
*   **Cognitive Separation:** The complex logic of translating web searches into structured Markdown is isolated from the logic of simulating geopolitical actions.
*   **Modularity:** The "Genesis" phase can be bypassed entirely if a user wants to load a pre-existing, manually crafted Wiki directory to run a simulation without the builder.
*   **Tool Safety:** The Builder can research through News and write to the Wiki without receiving unrelated mutation tools or control over the Wiki session identifier.

### Negative
*   **High Initial Latency:** The simulation takes significant time to start, as the Builder must complete multiple ReAct cycles and external API calls before the Orchestrator can take its first turn.
*   **Builder Bias:** The entire trajectory of the simulation is highly dependent on the quality of the Builder's initial search queries and its synthesis of the actors. A poor initialization dooms the simulation.
*   **Registry Coupling:** The Builder now depends on registry capability mappings being present for both `news_service` and `wiki_service`.

### Mitigation
*   The Builder's system prompt will include strict constraints to limit the maximum number of generated actors and state files to prevent context bloat and excessive startup times.
*   We will leverage the Hybrid API/MCP Architecture (ADR 006) to stream the Builder's progress to the frontend, providing UX feedback to the user while the world is being constructed.
*   Registry tests fail loudly when required capabilities are missing, role profiles drift from capability bindings, exposed tool names collide, or disallowed Wiki mutation tools appear in the World Builder profile.
