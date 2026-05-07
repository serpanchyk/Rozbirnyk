"""Orchestrate remote MCP tool discovery and LangChain integration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

from common.logging import setup_logger
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

logger = setup_logger("mcp_manager")

MCPTransport = Literal["streamable_http", "sse"]

WIKI_TOOL_ALLOWLISTS: dict[str, frozenset[str]] = {
    "world_builder": frozenset(
        {
            "read_state_file",
            "edit_state_file",
            "read_timeline",
            "read_actor_file",
            "edit_actor_file",
        }
    ),
    "simulation_orchestrator": frozenset(
        {
            "read_state_file",
            "edit_state_file",
            "read_timeline",
            "append_to_timeline",
            "read_actor_file",
            "edit_actor_file",
            "delete_file",
        }
    ),
    "actor": frozenset(
        {
            "read_state_file",
            "read_timeline",
            "append_to_actor_memory",
        }
    ),
    "report_agent": frozenset(
        {
            "read_state_file",
            "read_timeline",
            "read_actor_file",
        }
    ),
}


def filter_wiki_tools_for_role(tools: list[BaseTool], role: str) -> list[BaseTool]:
    """Filter discovered Wiki MCP tools for a specific agent role.

    Args:
        tools: Discovered LangChain tools from the Wiki MCP service.
        role: Agent role key from `WIKI_TOOL_ALLOWLISTS`.

    Returns:
        Tools whose names are allowed for the role.

    Raises:
        ValueError: If the role is not configured.
    """
    allowed = WIKI_TOOL_ALLOWLISTS.get(role)
    if allowed is None:
        raise ValueError(f"Unknown Wiki tool role: {role}")
    return [tool for tool in tools if tool.name in allowed]


class MCPResourceManager:
    """Manage lifecycle and adaptation of remote MCP resources.

    Data Flow: SSE Connection -> ClientSession -> load_mcp_tools -> LangChain Tools.
    """

    def __init__(
        self,
        host: str,
        port: int,
        transport: MCPTransport = "streamable_http",
    ) -> None:
        """Initialize connection parameters for a specific service.

        Args:
            host: The network hostname of the target MCP service.
            port: The port where the service exposes its SSE endpoint.
            transport: MCP HTTP transport variant to use.
        """
        self.transport = transport
        endpoint = "mcp/" if transport == "streamable_http" else "sse"
        self.url = f"http://{host}:{port}/{endpoint}"

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
            if self.transport == "streamable_http":
                async with streamablehttp_client(url=self.url) as (
                    read_stream,
                    write_stream,
                    _,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        yield await self._load_tools(session)
            else:
                async with sse_client(url=self.url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        yield await self._load_tools(session)
        except Exception as e:
            logger.error(
                "Failed to load tools from MCP server",
                extra={"error": str(e), "url": self.url},
            )
            raise

    async def _load_tools(self, session: ClientSession) -> list[BaseTool]:
        """Initialize a client session and adapt remote tools.

        Args:
            session: Initialized MCP client session.

        Returns:
            LangChain-compatible tools loaded from the session.
        """
        await session.initialize()
        tools = await load_mcp_tools(session)

        logger.info(
            "Successfully loaded remote tools",
            extra={"count": len(tools), "url": self.url},
        )
        return tools
