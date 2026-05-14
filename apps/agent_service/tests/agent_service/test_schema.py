"""Unit tests for agent service configuration schemas."""

import os
from unittest.mock import patch

import pytest
from agent_service.schema import AgentServiceConfig, MCPServerSettings
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


def test_agent_service_config_defaults_langsmith_tracing_to_disabled() -> None:
    """Verify tracing is opt-in in the default service config."""
    with patch.dict(os.environ, {}, clear=True):
        config = AgentServiceConfig(_env_file=None, model={"region_name": "us-east-1"})

    assert config.observability.langsmith.enabled is False
    assert config.observability.langsmith.project == "rozbirnyk"
    assert config.model.runtime.max_concurrency == 1
    assert config.model.runtime.min_seconds_between_calls == 1.0


def test_agent_service_config_rejects_invalid_bedrock_retry_bounds() -> None:
    """Verify Bedrock runtime config rejects inverted retry bounds."""
    with pytest.raises(ValidationError, match="retry_max_seconds"):
        AgentServiceConfig(
            _env_file=None,
            model={
                "region_name": "us-east-1",
                "runtime": {
                    "retry_base_seconds": 5,
                    "retry_max_seconds": 2,
                },
            },
        )
