"""
Pydantic schema for backend configuration.
"""

from functools import lru_cache

from common.config import BaseServiceConfig
from pydantic import BaseModel, ConfigDict, Field


class ServiceSettings(BaseModel):
    """Service-specific settings."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="backend")
    version: str = Field(default="0.1.0")
    port: int = Field(default=8000)


class LoggingSettings(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")
    level: str = Field(default="INFO")


class UpstreamSettings(BaseModel):
    """HTTP endpoints used by backend orchestration."""

    model_config = ConfigDict(extra="forbid")
    agent_service_url: str = Field(default="http://agent_service:8001")
    wiki_service_url: str = Field(default="http://wiki_service:8000")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ]
    )


class BackendConfig(BaseServiceConfig):
    """
    Main configuration model for backend.
    """

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    upstream: UpstreamSettings = Field(default_factory=UpstreamSettings)

    model_config = BaseServiceConfig.model_config | {"env_nested_delimiter": "__"}


@lru_cache
def get_config() -> BackendConfig:
    """
    Loads the configuration once and caches it.
    Subsequent calls return the cached memory instance.
    """
    return BackendConfig()
