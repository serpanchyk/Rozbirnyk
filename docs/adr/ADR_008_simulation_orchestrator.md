# ADR 009: Centralized Simulation Orchestration and State Mutation

## Status
Accepted

## Context
In the Rozbirnyk simulation engine, multiple LLM-backed Actors evaluate the world state and decide how to act based on their character sheets. If Actors were allowed to execute their own actions asynchronously and write directly to the Wiki, the system would immediately suffer from file-locking conflicts, logical contradictions, and hallucination cascades (e.g., an Actor declaring they have instantly conquered a continent without justification).

We require a "Game Master" mechanism to sequence turns, ruthlessly validate the logical consistency of proposed actions, enforce consequences, and maintain the integrity of the simulation's end conditions.

## Decision
We will implement the **Simulation Orchestrator** as a centralized, single-threaded ReAct loop that acts as the exclusive arbiter of the simulation. 

### 1. Turn Management (The Initiative System)
The Orchestrator determines which Actor acts next. Instead of a rigid round-robin sequence, the Orchestrator will use an event-driven heuristic. If Actor A takes an action that directly impacts Actor B, the Orchestrator prioritizes Actor B's turn to react, maintaining narrative momentum.

### 2. Action Validation Criteria
Actors do not *do* things; they *propose* things. The Orchestrator evaluates every proposal against three strict criteria:
*   **Policy Adherence:** Does the action violate the explicit "Policies" defined in the proposing Actor's character sheet?
*   **Logical Plausibility:** Is the action physically and economically possible given the current `States/` files? (e.g., A bankrupt organization cannot fund a massive global campaign).
*   **Causality Check:** Does the action directly follow from the current `Timeline.md`?

If an action fails validation, the Orchestrator rejects it and forces the Actor to propose an alternative, logging the failed attempt in the Actor's private memory.

### 3. Exclusive Mutation Rights
The Orchestrator is the **only** entity with access to "Write" MCP tools during the simulation. Upon validating an action, the Orchestrator:
1. Translates the action into environmental changes (`edit_state_file`).
2. Updates the acting and affected Actors' internal states (`edit_actor_file`, `append_to_memory`).
3. Writes the official, immutable record of the event to `Timeline.md`.

### 4. Termination Conditions
To prevent infinite loops, the Orchestrator evaluates stopping conditions at the end of every turn. The simulation ends when:
*   **Temporal Limit:** A predefined number of turns or simulated days is reached.
*   **Scenario Resolution:** The core "What if" tension has been decisively resolved (e.g., a specific bill is passed or a treaty is signed).
*   **Stagnation:** Actors repeatedly propose actions that yield no meaningful changes to the world state.

## Consequences

### Positive
*   **High Fidelity:** The rigorous validation criteria act as a hard firewall against LLM hallucinations, ensuring the forecast remains grounded in reality.
*   **ACID-like Guarantees:** By funneling all file I/O through a single Orchestrator loop, we completely eliminate race conditions and corrupted Markdown files.
*   **Explainability:** If a user questions why an event happened, the Orchestrator's ReAct logs provide a clear audit trail of the validation logic.

### Negative
*   **Context Window Bottleneck:** The Orchestrator must hold the Actor's proposal, the Actor's character sheet, the State summaries, and the Timeline in its context simultaneously. This makes it the most token-heavy and expensive component of the system.
*   **Single Point of Failure:** If the Orchestrator's logic falters or it misinterprets a state file, the entire simulation narrative derails.

### Mitigation
*   **Separation of Turn Logic:** To save LLM tokens, the "Turn Management" logic (deciding who goes next) can be offloaded to standard Python heuristics in LangGraph, reserving the LLM Orchestrator strictly for "Action Validation" and state mutation.
*   **Strict Output Parsing:** The Orchestrator will be forced to output its validation decisions in strict JSON formats before calling the MCP tools, ensuring predictable programmatic behavior.