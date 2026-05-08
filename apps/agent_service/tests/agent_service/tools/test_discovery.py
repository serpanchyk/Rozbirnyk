"""Unit tests for MCP tool discovery."""

from unittest.mock import AsyncMock, patch

import pytest
from agent_service.schema import MCPServersSettings
from agent_service.tools.discovery import MCPToolDiscovery


@pytest.mark.asyncio
async def test_discovery_error_identifies_server() -> None:
    """Verify discovery failures name the MCP server that failed."""
    settings = MCPServersSettings()

    with patch("agent_service.tools.discovery.MultiServerMCPClient") as client_cls:
        client = client_cls.return_value
        client.get_tools = AsyncMock(side_effect=ConnectionError("refused"))

        with pytest.raises(RuntimeError, match="Failed to discover tools from wiki_service"):
            await MCPToolDiscovery(settings).discover()
