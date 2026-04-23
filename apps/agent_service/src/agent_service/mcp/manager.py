"""Orchestrate remote MCP tool discovery and LangChain integration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from common.logging import setup_logger
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = setup_logger("mcp_manager")


class MCPResourceManager:
    """Manage lifecycle and adaptation of remote MCP resources.

    Data Flow: SSE Connection -> ClientSession -> load_mcp_tools -> LangChain Tools.
    """

    def __init__(self, host: str, port: int) -> None:
        """Initialize connection parameters for a specific service.

        Args:
            host: The network hostname of the target MCP service.
            port: The port where the service exposes its SSE endpoint.
        """
        self.url = f"http://{host}:{port}/sse"

    @asynccontextmanager
    async def discover_tools(self) -> AsyncGenerator[list[BaseTool], None]:
        """Connect to the server and adapt all available tools for LangChain.

        Yields:
            A list of tools ready for binding to a LangChain-compatible LLM.

        Raises:
            ConnectionError: If the remote service is unreachable.
        """
        logger.info("Discovering remote tools", extra={"url": self.url})
        try:
            async with sse_client(url=self.url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await load_mcp_tools(session)

                    logger.info(
                        "Successfully loaded remote tools",
                        extra={"count": len(tools), "url": self.url},
                    )
                    yield tools
        except Exception as e:
            logger.error(
                "Failed to load tools from MCP server",
                extra={"error": str(e), "url": self.url},
            )
            raise
