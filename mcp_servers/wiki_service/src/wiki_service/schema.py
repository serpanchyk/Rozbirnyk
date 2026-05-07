"""Define configuration schema for the Wiki Service."""

from functools import lru_cache

from common.config import BaseServiceConfig
from pydantic import BaseModel, ConfigDict, Field


class ServiceSettings(BaseModel):
    """Represent Wiki Service runtime settings."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="wiki_service")
    version: str = Field(default="0.1.0")
    port: int = Field(default=8000)


class LoggingSettings(BaseModel):
    """Represent logging settings for the service."""

    model_config = ConfigDict(extra="forbid")
    level: str = Field(default="INFO")


class StorageSettings(BaseModel):
    """Represent filesystem storage settings for wiki sessions."""

    model_config = ConfigDict(extra="forbid")
    root_dir: str = Field(default="/data/wiki")


class WikiServiceConfig(BaseServiceConfig):
    """Represent the complete Wiki Service configuration."""

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)

    model_config = BaseServiceConfig.model_config | {"env_nested_delimiter": "__"}


@lru_cache
def get_config() -> WikiServiceConfig:
    """Load and cache Wiki Service configuration."""
    return WikiServiceConfig()
