"""Tests for the cache module."""

import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest
from common import cache
from common.cache import (
    cache_tool,
    generate_cache_key,
    get_cached_result,
    get_redis,
    set_cached_result,
)


@pytest.fixture(autouse=True)
def reset_redis_client():
    """Fixture to reset the Redis client before and after each test."""
    cache._redis_client = None
    yield
    cache._redis_client = None


@patch("common.cache.redis.Redis")
def test_get_redis_singleton(mock_redis):
    """Test that get_redis returns a singleton Redis client instance."""
    client1 = get_redis()
    client2 = get_redis()

    mock_redis.assert_called_once()
    assert client1 is client2


@pytest.mark.asyncio
async def test_generate_cache_key():
    """Test that generate_cache_key creates a correct cache key."""
    query = "test_query"
    namespace = "test_space"
    expected_hash = hashlib.md5(query.encode("utf-8")).hexdigest()

    key = await generate_cache_key(namespace, query)

    assert key == f"cache:{namespace}:{expected_hash}"


@pytest.mark.asyncio
@patch("common.cache.get_redis")
async def test_get_cached_result_hit(mock_get_redis):
    """Test get_cached_result for a cache hit."""
    mock_client = AsyncMock()
    mock_client.get.return_value = '{"content": "data"}'
    mock_get_redis.return_value = mock_client

    result = await get_cached_result("test_key")

    assert result == {"content": "data"}
    mock_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
@patch("common.cache.get_redis")
async def test_get_cached_result_miss(mock_get_redis):
    """Test get_cached_result for a cache miss."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_get_redis.return_value = mock_client

    result = await get_cached_result("test_key")

    assert result is None
    mock_client.get.assert_called_once_with("test_key")


@pytest.mark.asyncio
@patch("common.cache.get_redis")
async def test_set_cached_result(mock_get_redis):
    """Test that set_cached_result correctly sets a value in the cache."""
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    data = {"data": "value"}

    await set_cached_result("test_key", data, ttl_seconds=10)

    mock_client.set.assert_called_once_with(
        name="test_key", value=json.dumps(data), ex=10
    )


@pytest.mark.asyncio
@patch("common.cache.set_cached_result")
@patch("common.cache.get_cached_result")
async def test_cache_tool_miss(mock_get, mock_set):
    """Test the cache_tool decorator on a cache miss."""
    mock_get.return_value = None

    @cache_tool(namespace="test_space", ttl_seconds=100)
    async def dummy_func(x):
        return x * 2

    result = await dummy_func(5)

    assert result == 10
    mock_get.assert_called_once()
    mock_set.assert_called_once()
    assert mock_set.call_args[0][1] == {"content": "10"}
    assert mock_set.call_args[0][2] == 100


@pytest.mark.asyncio
@patch("common.cache.set_cached_result")
@patch("common.cache.get_cached_result")
async def test_cache_tool_hit(mock_get, mock_set):
    """Test the cache_tool decorator on a cache hit."""
    mock_get.return_value = {"content": "cached_data"}

    @cache_tool(namespace="test_space", ttl_seconds=100)
    async def dummy_func(x):
        return x * 2

    result = await dummy_func(5)

    assert result == "cached_data"
    mock_get.assert_called_once()
    mock_set.assert_not_called()


@pytest.mark.asyncio
@patch("common.cache.set_cached_result")
@patch("common.cache.get_cached_result")
async def test_cache_tool_redis_get_error(mock_get, mock_set):
    """Test the cache_tool decorator when Redis 'get' raises an error."""
    mock_get.side_effect = ConnectionError

    @cache_tool(namespace="test_space")
    async def dummy_func(x):
        return x * 2

    result = await dummy_func(5)

    assert result == 10
    mock_get.assert_called_once()
    mock_set.assert_called_once()


@pytest.mark.asyncio
@patch("common.cache.set_cached_result")
@patch("common.cache.get_cached_result")
async def test_cache_tool_redis_set_error(mock_get, mock_set):
    """Test the cache_tool decorator when Redis 'set' raises an error."""
    mock_get.return_value = None
    mock_set.side_effect = ConnectionError

    @cache_tool(namespace="test_space")
    async def dummy_func(x):
        return x * 2

    result = await dummy_func(5)

    assert result == 10
    mock_get.assert_called_once()
    mock_set.assert_called_once()
