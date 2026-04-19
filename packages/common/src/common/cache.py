"""Provides a Redis-backed caching layer for asynchronous tool functions.

This module offers a decorator (`cache_tool`) and utility functions to
cache the results of expensive operations, reducing latency and external API calls.
It handles key generation, data serialization, and graceful degradation
when Redis is unavailable.
"""

import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any

import redis.asyncio as redis
from pydantic import Field
from pydantic_settings import BaseSettings

from common.logging import setup_logger

logger = setup_logger("cache")


class CacheSettings(BaseSettings):
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = 0


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Initialize and return a singleton Redis client instance.

    Uses `CacheSettings` for configuration and ensures only one connection
    pool is created per application instance.

    Returns:
        An active redis.Redis client instance.
    """
    global _redis_client
    if _redis_client is None:
        settings = CacheSettings()
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
    return _redis_client


async def generate_cache_key(namespace: str, query: str) -> str:
    """Generate a deterministic MD5 hash key for Redis storage.

    Args:
        namespace: The cache namespace (e.g., 'news_api').
        query: The input string to hash (e.g., a search query).

    Returns:
        A formatted string to be used as a Redis key.
    """
    query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
    return f"cache:{namespace}:{query_hash}"


async def get_cached_result(key: str) -> Any | None:
    """Retrieve and deserialize a JSON object from a Redis cache.

    Args:
        key: The Redis key to fetch.

    Returns:
        The deserialized Python dictionary if the key exists, otherwise None.
    """
    redis_client = get_redis()
    result = await redis_client.get(key)
    if result:
        return json.loads(str(result))
    return None


async def set_cached_result(
    key: str, data: dict[str, Any], ttl_seconds: int = 43200
) -> None:
    """Serialize and store data in Redis with a Time-To-Live (TTL).

    Args:
        key: The Redis key under which to store the data.
        data: The Python dictionary to serialize and store.
        ttl_seconds: The time-to-live for the cache entry in seconds.
    """
    redis_client = get_redis()
    await redis_client.set(name=key, value=json.dumps(data), ex=ttl_seconds)


def cache_tool(
    namespace: str, ttl_seconds: int = 43200
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator to cache the results of an async function.

    The decorator intercepts function calls, checks for a cached result in Redis,
    and only executes the decorated function on a cache miss. Results are
    stored in Redis with a specified TTL.

    It generates a deterministic cache key based on the function's arguments.

    Args:
        namespace: A string to identify the cache category (e.g., 'weather_api').
        ttl_seconds: The time-to-live for cached results in seconds.

    Returns:
        A decorator that can be applied to an async function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:

            arg_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
            query_hash = hashlib.md5(arg_str.encode("utf-8")).hexdigest()
            cache_key = f"cache:{namespace}:{query_hash}"

            try:
                cached_data = await get_cached_result(cache_key)
                if cached_data:
                    logger.info(
                        "Cache HIT", extra={"cache_hit": True, "namespace": namespace}
                    )
                    return cached_data.get("content", "")
            except ConnectionError:
                logger.warning(
                    "Redis GET failed. Bypassing cache.", extra={"namespace": namespace}
                )

            logger.info(
                "Cache MISS. Executing tool.",
                extra={"cache_hit": False, "namespace": namespace},
            )

            result = await func(*args, **kwargs)

            try:
                await set_cached_result(
                    cache_key, {"content": str(result)}, ttl_seconds
                )
            except ConnectionError:
                logger.error(
                    "Redis SET failed. Result not cached.",
                    extra={"namespace": namespace},
                )

            return result

        return wrapper

    return decorator
