# ADR 008: Actor Identity and State Management via Character Sheets

## Status
Accepted

## Context
In the Rozbirnyk simulation, Actors represent dynamic entities (e.g., political parties, corporations, public figures). To behave logically, an LLM acting as an entity requires persistent goals, constraints, and memory. 

If this context is left to conversational history or unstructured generation, Actors will experience "character drift"—losing track of their motivations or acting out of character. Furthermore, the World Builder needs a standardized format to translate real-world news into simulated agents, and the Orchestrator needs a reliable way to update an Actor's state as the simulation progresses.

## Decision
We will define Actor state using a standardized Markdown "Character Sheet" stored in the `Actors/` directory. This file serves as the definitive System Prompt for the Actor during its ReAct loop.

### 1. The Character Sheet Schema
Every `Actors/{actor_name}.md` file will strictly adhere to the following structure:

*   **Title & Short Description:** (Required by ADR 005 for the Summary Index).
*   **Identity & Characteristics:** Core, immutable traits (e.g., "Risk-averse," "Technocratic," "Ideologically driven by X").
*   **Current State:** The actor's immediate geopolitical or economic standing (e.g., "Currently facing a PR crisis," "Holding a majority in parliament").
*   **Active Goals:** A prioritized list of what the actor is trying to achieve in the simulation. (These provide the stopping condition for the Actor's ReAct loop).
*   **Policies (Rules of Engagement):** Strict constraints on behavior (e.g., "Will never ally with Actor Y," "Refuses to use illegal methods"). This acts as a guardrail against LLM hallucinations.
*   **Private Memory:** A chronological list of internal thoughts, grudges, or secret knowledge that is *not* public on the `Timeline.md`.

### 2. The Actor Lifecycle
*   **Genesis (World Builder):** The World Builder synthesizes news via Tavily to populate the initial Identity, Goals, and Policies.
*   **Execution (Actor Loop):** On its turn, the Actor receives its own actor files from the Wiki API, alongside the title and short description of every Wiki file. It may use MCP tools to read complete state files, read the timeline, and append entries to its own private memory.
*   **Mutation Boundary:** Actors cannot edit state files, actor files, the timeline, or delete Wiki files. They may only append private memory entries through `append_to_actor_memory`; changes to goals, policies, public world state, and timeline events remain under the Orchestrator's validation and mutation flow.

## Consequences

### Positive
*   **Behavioral Consistency:** The strict "Policies" and "Characteristics" sections force the LLM to stay in character, improving the realism of the forecast.
*   **Explainable AI:** If an Actor makes a bizarre move, developers can look at the `Actors/*.md` file to see if a corrupted Goal or Memory caused it.
*   **Clean Orchestration:** By separating private internal memory from public state (`Timeline.md`), we can simulate deception, secret alliances, and asymmetric information without giving Actors authority to mutate shared world facts.

### Negative
*   **Context Bloat:** As the simulation runs, the "Private Memory" section of the Markdown file will continuously grow, eventually consuming too much of the context window and increasing API costs.
*   **Rigidity:** If the World Builder defines the Policies too strictly at the start, the Actor might become paralyzed and unable to react dynamically to completely unprecedented world events.

### Mitigation
*   **Memory Consolidation:** The Orchestrator will be equipped with a specific tool that monitors the length of Actor files. When the "Private Memory" section exceeds a certain token limit, the Orchestrator will trigger a prompt to summarize older memories into broader beliefs.
