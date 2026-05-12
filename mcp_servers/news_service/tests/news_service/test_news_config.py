"""Unit tests for news service configuration parsing."""

import pytest
from news_service.schema import NewsServiceConfig


def test_news_service_config_reads_flat_tavily_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the documented TAVILY_API_KEY env var populates service settings."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-api-key")

    config = NewsServiceConfig(_env_file=None)

    assert config.tavily_api_key == "test-api-key"
    assert config.tavily.api_key == "test-api-key"
