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


class BackendConfig(BaseServiceConfig):
    """
    Main configuration model for backend.
    """

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = BaseServiceConfig.model_config | {"env_nested_delimiter": "__"}


@lru_cache
def get_config() -> BackendConfig:
    """
    Loads the configuration once and caches it.
    Subsequent calls return the cached memory instance.
    """
    return BackendConfig()
