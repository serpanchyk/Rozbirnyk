"""Unit tests for the RemoteMCPClient network layer."""

from unittest.mock import AsyncMock, patch

import pytest
from agent_service.mcp.client import RemoteMCPClient


@pytest.mark.asyncio
async def test_get_session_lifecycle():
    """Verify that the client initializes the session and manages lifecycle."""
    host, port = "test-service", 8000
    client = RemoteMCPClient(host, port)

    mock_read = AsyncMock()
    mock_write = AsyncMock()
    mock_session = AsyncMock()

    with patch("agent_service.mcp.client.sse_client") as mock_sse:
        mock_sse.return_value.__aenter__.return_value = (mock_read, mock_write)

        with patch("agent_service.mcp.client.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            async with client.get_session() as session:
                assert session is mock_session
                mock_session.initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_connection_error():
    """Verify that the client logs and re-raises connection exceptions."""
    client = RemoteMCPClient("invalid-host", 1234)

    with patch(
        "agent_service.mcp.client.sse_client",
        side_effect=Exception("Connection refused"),
    ):
        with pytest.raises(Exception) as exc:
            async with client.get_session():
                pass
        assert "Connection refused" in str(exc.value)
