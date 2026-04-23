"""Unit tests for the News Service MCP tools.

Data Flow: Pytest Framework -> Mocked Tavily Client
/ Mocked Cache Layer -> Tool Execution -> Assertion
"""

from unittest.mock import MagicMock, patch

import pytest
from news_service.main import (
    extract_article_content,
    search_deep_research,
    search_recent_news,
)


@pytest.fixture
def mock_config():
    """Provide a mocked configuration with a dummy Tavily API key."""
    with patch("news_service.main.get_config") as mock_get_config:
        mock_settings = MagicMock()
        mock_settings.tavily.api_key = "test_api_key_123"
        mock_get_config.return_value = mock_settings
        yield mock_get_config


@pytest.fixture
def mock_tavily():
    """Provide a mocked TavilyClient instance to intercept API calls."""
    with patch("news_service.main.TavilyClient") as mock_client_class:
        mock_instance = MagicMock()
        mock_client_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_cache():
    """Bypass the Redis caching layer to ensure tools execute their core logic."""
    with (
        patch("common.cache.get_cached_result", return_value=None),
        patch("common.cache.set_cached_result"),
    ):
        yield


@pytest.mark.asyncio
async def test_search_recent_news(mock_config, mock_tavily, mock_cache):
    """Verify that the recent news tool formats Tavily search parameters correctly.

    Args:
        mock_config: The mocked configuration fixture.
        mock_tavily: The mocked Tavily API client fixture.
        mock_cache: The mocked Redis cache fixture.
    """
    expected_response = {"results": [{"title": "Test News", "url": "http://test"}]}
    mock_tavily.search.return_value = expected_response

    result = await search_recent_news("European Parliament", days=5)

    assert result == expected_response
    mock_tavily.search.assert_called_once_with(
        query="European Parliament",
        topic="news",
        days=5,
        include_raw_content=False,
    )


@pytest.mark.asyncio
async def test_search_deep_research(mock_config, mock_tavily, mock_cache):
    """Verify that the deep research tool enforces the advanced search depth flag.

    Args:
        mock_config: The mocked configuration fixture.
        mock_tavily: The mocked Tavily API client fixture.
        mock_cache: The mocked Redis cache fixture.
    """
    expected_response = {
        "results": [{"title": "Historical Context", "url": "http://test"}]
    }
    mock_tavily.search.return_value = expected_response

    result = await search_deep_research("Global warming policies")

    assert result == expected_response
    mock_tavily.search.assert_called_once_with(
        query="Global warming policies",
        search_depth="advanced",
        include_raw_content=False,
    )


@pytest.mark.asyncio
async def test_extract_article_content(mock_config, mock_tavily, mock_cache):
    """Verify that the extraction tool correctly passes URL lists to the API.

    Args:
        mock_config: The mocked configuration fixture.
        mock_tavily: The mocked Tavily API client fixture.
        mock_cache: The mocked Redis cache fixture.
    """
    expected_response = {"results": [{"raw_content": "Extracted text body."}]}
    mock_tavily.extract.return_value = expected_response
    target_urls = ["https://example.com/article1", "https://example.com/article2"]

    result = await extract_article_content(target_urls)

    assert result == expected_response
    mock_tavily.extract.assert_called_once_with(urls=target_urls)
