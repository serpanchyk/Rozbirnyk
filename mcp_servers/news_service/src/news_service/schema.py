"""Pydantic schema for news_service configuration."""

from functools import lru_cache

from common.config import BaseServiceConfig
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServiceSettings(BaseModel):
    """Service-specific settings."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="news_service")
    version: str = Field(default="0.1.0")
    port: int = Field(default=8000)


class LoggingSettings(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")
    level: str = Field(default="INFO")


class TavilySettings(BaseModel):
    """Tavily configuration."""

    model_config = ConfigDict(extra="forbid")
    api_key: str = Field(min_length=1)


class NewsServiceConfig(BaseServiceConfig):
    """Main configuration model for news_service."""

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    tavily_api_key: str = Field(min_length=1, alias="TAVILY_API_KEY")

    model_config = BaseServiceConfig.model_config | {
        "populate_by_name": True,
        "env_nested_delimiter": "__",
    }

    @field_validator("tavily_api_key")
    @classmethod
    def validate_tavily_api_key(cls, value: str) -> str:
        """Reject placeholder Tavily values copied from examples."""
        if value.strip() == "replace-me":
            msg = "TAVILY_API_KEY must be set to a real value"
            raise ValueError(msg)
        return value

    @property
    def tavily(self) -> TavilySettings:
        """Expose Tavily credentials through the existing nested interface."""
        return TavilySettings(api_key=self.tavily_api_key)


@lru_cache
def get_config() -> NewsServiceConfig:
    """Load and cache the service configuration."""
    return NewsServiceConfig()
