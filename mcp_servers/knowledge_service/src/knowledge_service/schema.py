"""
Pydantic schema for knowledge_service configuration.
"""

from functools import lru_cache

from common.config import BaseServiceConfig
from pydantic import BaseModel, ConfigDict, Field


class ServiceSettings(BaseModel):
    """Service-specific settings."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="knowledge_service")
    version: str = Field(default="0.1.0")
    port: int = Field(default=8002)


class LoggingSettings(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")
    level: str = Field(default="INFO")


class KnowledgeServiceConfig(BaseServiceConfig):
    """
    Main configuration model for knowledge_service.
    """

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = BaseServiceConfig.model_config | {"env_nested_delimiter": "__"}


@lru_cache
def get_config() -> KnowledgeServiceConfig:
    """
    Loads the configuration once and caches it.
    Subsequent calls return the cached memory instance.
    """
    return KnowledgeServiceConfig()
