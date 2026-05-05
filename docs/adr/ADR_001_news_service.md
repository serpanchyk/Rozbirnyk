# ADR 001: Grounded World State via Cached MCP News Service

## Status
Accepted

## Context
A simulation's utility depends on "grounding"—how accurately it reflects reality at the moment of a "What if" query. Traditional LLM training data is static and suffers from knowledge cutoffs. To build a dynamic World Wiki, the system needs to fetch real-time data. 

However, calling external search APIs (Tavily) directly within agent loops presents several challenges:
1. **Latency:** External network calls slow down the ReAct cycles.
2. **Cost/Rate Limits:** Frequent duplicate calls rapidly consume API credits.
3. **Consistency:** Multiple agents (Builder, Orchestrator, Actors) must see a synchronized version of "reality" within a single simulation session to avoid logical contradictions.

## Decision
We will implement a dedicated **News Service MCP** as the primary data ingestion node. This service standardizes world-state acquisition through three specialized tools and a Redis-backed caching layer.

### 1. Technical Implementation
*   **Tooling Layer:** 
    * `search_recent_news`: Surface-level updates (3-day window) for current events.
    * `search_deep_research`: Advanced depth search for historical context and entity backgrounds.
    * `extract_article_content`: Full-text scraping to populate detailed Wiki files.
*   **Caching Strategy:** A shared `@cache_tool` decorator manages data freshness (e.g., 30-minute TTL for news, 24-hour TTL for deep research).
*   **Observability:** Structured JSON logging with injected Trace IDs to track data flow from the external API into the simulation's "World Wiki."

### 2. Operational Flow
The **World Builder** agent uses these tools to transform search results into a structured directory of `.md` files (`States/` and `Actors/`). This ensures that while the source is live web data, the agents interact with a stable, file-based "ground truth" during the simulation.

## Consequences

### Positive
*   **Real-time Relevance:** Simulations reflect unfolding events rather than static training data.
*   **Efficiency:** Redis caching significantly reduces latency and API costs for repetitive queries.
*   **Decoupling:** The simulation logic is independent of the search provider. Switching from Tavily to another provider only requires updating the MCP service, not the agents.
*   **Traceability:** Clear logs provide an audit trail of why the World Builder chose specific facts for the simulation.

### Negative
*   **Infrastructure Dependency:** Requires a running Redis instance and a stable internet connection for the initial build phase.
*   **Stale Data Risks:** A cache TTL of 30 minutes means the simulation might miss "breaking news" that occurs mid-session unless the cache is bypassed.
*   **Complexity:** Adds a layer of networking (SSE/HTTP) and configuration (Pydantic-based `NewsServiceConfig`) to the project.

### Mitigation
*   TTL values are tuned per tool based on the volatility of the information.
*   The system uses an asynchronous `FastMCP` event loop to handle concurrent tool requests from multiple agents without blocking.