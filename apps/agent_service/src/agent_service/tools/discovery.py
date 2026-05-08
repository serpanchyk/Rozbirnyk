"""Discover LangChain tools from configured MCP servers."""

from typing import cast

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import (
    SSEConnection,
    StdioConnection,
    StreamableHttpConnection,
    WebsocketConnection,
)

from agent_service.schema import MCPServersSettings

type MCPConnection = (
    StdioConnection | SSEConnection | StreamableHttpConnection | WebsocketConnection
)

DISCOVERED_SERVER_NAMES = ("wiki_service", "news_service")


class MCPToolDiscovery:
    """Discover tools from the MCP servers used by agent graphs."""

    def __init__(self, settings: MCPServersSettings) -> None:
        """Initialize discovery from service connection settings.

        Args:
            settings: Agent service MCP server configuration.
        """
        self._settings = settings

    async def discover(self) -> dict[str, list[BaseTool]]:
        """Return discovered tools grouped by MCP server name."""
        client = MultiServerMCPClient(self._build_connections())
        discovered: dict[str, list[BaseTool]] = {}
        for server_name in DISCOVERED_SERVER_NAMES:
            discovered[server_name] = await client.get_tools(server_name=server_name)
        return discovered

    def _build_connections(self) -> dict[str, MCPConnection]:
        """Build MultiServerMCPClient connection dictionaries."""
        connections: dict[str, MCPConnection] = {}
        for server_name in DISCOVERED_SERVER_NAMES:
            server = getattr(self._settings, server_name)
            connections[server_name] = cast(
                MCPConnection, {"transport": server.transport, "url": server.url}
            )
        return connections
