# Vision: Simulation

## Vision Statement
To create an autonomous world-modeling engine that transforms "What if" queries into dynamic, multi-agent simulations. By grounding agents in real-time news and structured wiki environments, the system explores plausible future scenarios through the lens of actor-driven logic and environmental feedback.

## Core Principles
* **Grounded Autonomy:** Every simulation starts with the current state of the world via live data, not static training knowledge.
* **Persistent State:** The "World Wiki" acts as the single source of truth, ensuring agents interact with a consistent and evolving environment.
* **Separation of Concerns:** Distinct roles for initialization (Builder), execution (Orchestrator), and agency (Actors) to prevent logical bleeding.

## Strategic Goals
* **Dynamic World Generation:** Automatically synthesize complex entities (orgs, people, nations) with specific motivations based on current events.
* **Traceable Chronology:** Maintain a strict `Timeline.md` that serves as a verifiable audit trail of the simulation's evolution.
* **MCP Integration:** Standardize all world interactions (reading/writing state) through a Model Context Protocol layer for modularity.

## Non-Goals
* **Real-time Graphics:** This is a text-based logic and forecasting tool, not a visual simulator.
* **Predictive Certainty:** The goal is to explore *possibilities* and emergent behaviors, not to provide a singular, "correct" prediction of the future.
* **Long-term Memory (v1):** For this phase, focus is on the immediate session; cross-simulation learning is out of scope.

## The Simulation Loop
1. **The Spark:** User provides a "What if" scenario.
2. **The Genesis:** Builder gathers news and populates the Wiki directory.
3. **The Play:** Orchestrator cycles through Actors; Actors propose actions based on their goals; Orchestrator validates and updates the Wiki.
4. **The Synthesis:** Report Agent distills the log into a narrative of that specific timeline.