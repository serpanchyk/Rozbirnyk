"""Expose Tavily search capabilities as an MCP
server for the multi-agent forecasting system.

Acts as the primary data ingestion node for the
World Builder Agent, enabling it to autonomously
fetch recent news, research historical context,
and extract full article content to construct
the simulation wiki state.

Data Flow: MCP Client Request -> Redis Cache Layer
-> Tavily API -> Contextual Logging -> MCP Client Response.

Logging Context: Emits structured JSON logs
containing execution metadata and query parameters.
Relies on injected trace IDs from the contextvars
ecosystem for distributed observability.

Async Behavior: Tool execution and SSE HTTP transport
are managed asynchronously by the internal
FastMCP Starlette event loop.
"""

from typing import Any

from common.cache import cache_tool
from common.logging import setup_logger
from fastmcp import FastMCP
from tavily import TavilyClient

from news_service.schema import get_config

logger = setup_logger("news_service")
mcp = FastMCP("Rozbirnyk News Service")


@mcp.tool
@cache_tool(namespace="news_recent", ttl_seconds=1800)
async def search_recent_news(query: str, days: int = 3) -> Any:
    """Fetch fast, surface-level news updates to populate current world events.

    Data Flow: Input -> Set Trace ID -> Cache Check -> Query Tavily API -> Output

    Args:
        query: The specific event or entity to research.
        days: The historical window to constrain the search.

    Returns:
        A collection of recent headlines, URLs, and short snippets.
    """
    config = get_config()
    logger.info("Executing recent news search", extra={"query": query, "days": days})

    client = TavilyClient(api_key=config.tavily.api_key)
    return client.search(
        query=query,
        topic="news",
        days=days,
        include_raw_content=False,
    )


@mcp.tool
@cache_tool(namespace="news_deep", ttl_seconds=86400)
async def search_deep_research(query: str) -> Any:
    """Execute an advanced search to gather comprehensive background data.

    Data Flow: Input -> Set Trace ID -> Cache Check -> Query Tavily API -> Output

    Args:
        query: The overarching topic or historical context to investigate.

    Returns:
        Detailed search results from authoritative sources,
        spanning a broader timeframe.
    """
    logger.info("Executing deep research search", extra={"query": query})

    config = get_config()
    client = TavilyClient(api_key=config.tavily.api_key)
    return client.search(
        query=query,
        search_depth="advanced",
        include_raw_content=False,
    )


@mcp.tool
@cache_tool(namespace="news_extract", ttl_seconds=86400)
async def extract_article_content(urls: list[str]) -> Any:
    """Extract raw text content from specific web URLs for deep analysis.

    Data Flow: Input -> Set Trace ID -> Cache Check -> Scrape via Tavily API -> Output

    Args:
        urls: Target web addresses obtained from previous search operations.

    Returns:
        Full raw text content extracted from the provided URLs.
    """
    config = get_config()
    logger.info("Executing article content extraction", extra={"url_count": len(urls)})

    client = TavilyClient(api_key=config.tavily.api_key)
    return client.extract(urls=urls)


if __name__ == "__main__":
    config = get_config()
    logger.info(
        "Initializing News Service MCP",
        extra={"host": "0.0.0.0", "port": config.service.port, "transport": "sse"},
    )
    mcp.run(transport="sse", host="0.0.0.0", port=config.service.port)
