"""Unit tests for agent service configuration schemas."""

import pytest
from agent_service.schema import MCPServerSettings
from pydantic import ValidationError


def test_mcp_server_settings_builds_default_http_url() -> None:
    """Verify MCP settings expose the computed streamable HTTP URL."""
    settings = MCPServerSettings(host="wiki_service", port=8000)

    assert settings.url == "http://wiki_service:8000/mcp/"


def test_mcp_server_settings_builds_sse_url() -> None:
    """Verify MCP settings expose the computed SSE URL."""
    settings = MCPServerSettings(
        host="news_service",
        port=8000,
        transport="sse",
    )

    assert settings.url == "http://news_service:8000/sse"


def test_mcp_server_settings_rejects_invalid_host() -> None:
    """Verify invalid MCP hosts fail during configuration validation."""
    with pytest.raises(ValidationError):
        MCPServerSettings(host="", port=8000)


def test_mcp_server_settings_rejects_invalid_port() -> None:
    """Verify invalid MCP ports fail during configuration validation."""
    with pytest.raises(ValidationError):
        MCPServerSettings(host="wiki_service", port=0)
