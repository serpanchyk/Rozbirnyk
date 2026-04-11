"""Unit tests for the Redis caching layer."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from common.cache import (
    cache_tool,
    generate_cache_key,
    get_cached_result,
    set_cached_result,
)


@pytest.fixture(autouse=True)
def mock_redis(mocker: MagicMock) -> AsyncMock:
    """
    Mocks the global _redis_client to ensure tests are deterministic
    and do not require a live Redis instance.
    """
    mock_client = AsyncMock()
    mocker.patch("common.cache._redis_client", mock_client)
    return mock_client


@pytest.mark.asyncio
async def test_generate_cache_key() -> None:
    """
    Validates that cache keys are generated deterministically using MD5.
    """
    namespace = "test_space"
    query = "test_query"
    expected_hash = "8ba4b3b890a501a30fa140ed504d60fc"

    result = await generate_cache_key(namespace, query)

    assert result == f"cache:{namespace}:{expected_hash}"


@pytest.mark.asyncio
async def test_get_cached_result_hit(mock_redis: AsyncMock) -> None:
    """
    Validates data retrieval and JSON deserialization on a cache hit.
    """
    mock_redis.get.return_value = '{"key": "value"}'

    result = await get_cached_result("some_key")

    assert result == {"key": "value"}
    mock_redis.get.assert_called_once_with("some_key")


@pytest.mark.asyncio
async def test_get_cached_result_miss(mock_redis: AsyncMock) -> None:
    """
    Validates that None is returned when the cache key does not exist.
    """
    mock_redis.get.return_value = None

    result = await get_cached_result("some_key")

    assert result is None


@pytest.mark.asyncio
async def test_set_cached_result(mock_redis: AsyncMock) -> None:
    """
    Validates JSON serialization and Redis SET call with correct TTL.
    """
    data = {"test": "data"}

    await set_cached_result("some_key", data, ttl_seconds=100)

    mock_redis.set.assert_called_once_with(
        name="some_key", value=json.dumps(data), ex=100
    )


@pytest.mark.asyncio
async def test_cache_tool_hit(mock_redis: AsyncMock) -> None:
    """
    Validates that the decorated function is completely bypassed
    when a valid cache entry is found.
    """
    mock_redis.get.return_value = '{"content": "cached_response"}'
    mock_func = AsyncMock()
    decorated_func = cache_tool("test_space")(mock_func)

    result = await decorated_func("arg1", kwarg1="val1")

    assert result == "cached_response"
    mock_func.assert_not_called()


@pytest.mark.asyncio
async def test_cache_tool_miss(mock_redis: AsyncMock) -> None:
    """
    Validates that the decorated function executes on a cache miss
    and the result is subsequently cached.
    """
    mock_redis.get.return_value = None
    mock_func = AsyncMock(return_value="live_response")
    decorated_func = cache_tool("test_space", ttl_seconds=500)(mock_func)

    result = await decorated_func("arg1", kwarg1="val1")

    assert result == "live_response"
    mock_func.assert_called_once_with("arg1", kwarg1="val1")
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
async def test_cache_tool_redis_get_failure(mock_redis: AsyncMock) -> None:
    """
    Validates graceful degradation: if Redis GET fails, the system
    should execute the tool rather than crashing the pipeline.
    """
    mock_redis.get.side_effect = ConnectionError("Redis is down")
    mock_func = AsyncMock(return_value="live_response_fallback")
    decorated_func = cache_tool("test_space")(mock_func)

    result = await decorated_func("arg1")

    assert result == "live_response_fallback"
    mock_func.assert_called_once_with("arg1")


@pytest.mark.asyncio
async def test_cache_tool_redis_set_failure(mock_redis: AsyncMock) -> None:
    """
    Validates graceful degradation: if Redis SET fails after tool execution,
    the system should still return the successful tool result.
    """
    mock_redis.get.return_value = None
    mock_redis.set.side_effect = ConnectionError("Redis went down during processing")
    mock_func = AsyncMock(return_value="live_response")
    decorated_func = cache_tool("test_space")(mock_func)

    result = await decorated_func("arg1")

    assert result == "live_response"
    mock_func.assert_called_once_with("arg1")
