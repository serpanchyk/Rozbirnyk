# MCP Service Interactions

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Agent Service
    participant Registry as Tool Registry
    participant News as News MCP Service
    participant Wiki as Wiki Service
    participant Tavily as Tavily API
    participant Files as World Wiki Files

    Agent->>Registry: resolve tools for role and session
    Registry-->>Agent: role-scoped News and Wiki tools
    Agent->>News: search_recent_news(query)
    News->>Tavily: search current sources
    Tavily-->>News: source summaries and links
    News-->>Agent: normalized research result
    Agent->>News: extract_article_content(url)
    News->>Tavily: extract article
    Tavily-->>News: article content
    News-->>Agent: extracted context
    Agent->>Wiki: write_state(session_id, path, content)
    Wiki->>Files: persist States/*.md
    Files-->>Wiki: write result
    Wiki-->>Agent: confirmation
    Agent->>Wiki: append_timeline_event(session_id, event)
    Wiki->>Files: append Timeline.md
    Files-->>Wiki: append result
    Wiki-->>Agent: confirmation
```

