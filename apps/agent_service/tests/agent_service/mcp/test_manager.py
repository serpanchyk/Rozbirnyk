"""Unit tests for the MCPResourceManager using langchain-mcp-adapters."""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent_service.mcp.manager import MCPResourceManager, filter_wiki_tools_for_role
from langchain_core.tools import BaseTool


@pytest.fixture
def mock_mcp_infrastructure():
    """Provide a mocked environment for MCP client and session.

    Yields:
        A tuple containing (mock_read, mock_write, mock_session).
    """
    mock_read = AsyncMock()
    mock_write = AsyncMock()
    mock_session = AsyncMock()
    yield mock_read, mock_write, mock_session


@pytest.mark.asyncio
async def test_discover_tools_success(mock_mcp_infrastructure):
    """Verify that the manager initializes a session and adapts tools correctly.

    Data Flow: Mock SSE -> ClientSession -> load_mcp_tools -> Tool List.
    """
    _, _, mock_session = mock_mcp_infrastructure
    manager = MCPResourceManager("test-host", 8000)
    mock_tools = [MagicMock(spec=BaseTool), MagicMock(spec=BaseTool)]

    with patch("agent_service.mcp.manager.streamablehttp_client") as mock_client:
        mock_client.return_value.__aenter__.return_value = (
            AsyncMock(),
            AsyncMock(),
            MagicMock(),
        )

        with patch("agent_service.mcp.manager.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            with patch(
                "agent_service.mcp.manager.load_mcp_tools", return_value=mock_tools
            ) as mock_load:
                async with manager.discover_tools() as tools:
                    assert len(tools) == 2
                    assert tools == mock_tools
                    mock_session.initialize.assert_awaited_once()
                    mock_load.assert_awaited_once_with(mock_session)
                    mock_client.assert_called_once_with(url="http://test-host:8000/mcp/")


@pytest.mark.asyncio
async def test_discover_tools_sse_compatibility(mock_mcp_infrastructure):
    """Verify the manager can still connect to legacy SSE MCP services."""
    _, _, mock_session = mock_mcp_infrastructure
    manager = MCPResourceManager("test-host", 8000, transport="sse")
    mock_tools = [MagicMock(spec=BaseTool)]

    with patch("agent_service.mcp.manager.sse_client") as mock_sse:
        mock_sse.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        with patch("agent_service.mcp.manager.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            with patch("agent_service.mcp.manager.load_mcp_tools", return_value=mock_tools):
                async with manager.discover_tools() as tools:
                    assert tools == mock_tools
                    mock_sse.assert_called_once_with(url="http://test-host:8000/sse")


@pytest.mark.asyncio
async def test_discover_tools_connection_failure():
    """Verify that the manager logs errors and raises
    exceptions on connection failure."""
    manager = MCPResourceManager("invalid-host", 1234)

    with patch(
        "agent_service.mcp.manager.streamablehttp_client",
        side_effect=Exception("Network unreachable"),
    ):
        with pytest.raises(Exception) as exc:
            async with manager.discover_tools():
                pass

        assert "Network unreachable" in str(exc.value)


def test_filter_wiki_tools_for_role():
    """Verify Wiki tools are filtered to the documented role allowlist."""
    tools: list[BaseTool] = []
    for name in ["read_state_file", "edit_state_file", "delete_file"]:
        tool = MagicMock(spec=BaseTool)
        tool.name = name
        tools.append(cast(BaseTool, tool))

    filtered = filter_wiki_tools_for_role(tools, "actor")

    assert [tool.name for tool in filtered] == ["read_state_file"]


def test_filter_wiki_tools_unknown_role():
    """Verify unknown Wiki roles fail loudly."""
    with pytest.raises(ValueError, match="Unknown"):
        filter_wiki_tools_for_role([], "unknown")
