"""Define Pydantic schemas for agent_service configuration."""

from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlparse

from common.config import BaseServiceConfig
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServiceSettings(BaseModel):
    """Service-specific settings."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="agent_service")
    version: str = Field(default="0.1.0")
    port: int = Field(default=8001)


class LoggingSettings(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")
    level: str = Field(default="INFO")


class LangSmithSettings(BaseModel):
    """Optional LangSmith tracing configuration."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(default=False)
    api_key: str | None = Field(default=None)
    project: str = Field(default="rozbirnyk", min_length=1)
    endpoint: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_enabled_configuration(self) -> Self:
        """Require a real API key when LangSmith tracing is enabled."""
        if not self.enabled:
            return self
        api_key = (self.api_key or "").strip()
        if api_key and api_key != "lsv2_pt_replace_me":
            return self
        msg = (
            "observability.langsmith.api_key must be set to a real value when "
            "LangSmith tracing is enabled"
        )
        raise ValueError(msg)


class ObservabilitySettings(BaseModel):
    """Observability integrations."""

    model_config = ConfigDict(extra="forbid")
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)


type ModelProvider = Literal["bedrock"]


class ModelRuntimeSettings(BaseModel):
    """Configure provider request pacing and retries."""

    model_config = ConfigDict(extra="forbid")
    max_concurrency: int = Field(default=1, gt=0)
    min_seconds_between_calls: float = Field(default=2.0, ge=0.0)
    max_retries: int = Field(default=10, ge=0)
    retry_base_seconds: float = Field(default=1.0, gt=0.0)
    retry_max_seconds: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def validate_retry_bounds(self) -> Self:
        """Ensure retry caps are internally consistent."""
        if self.retry_max_seconds < self.retry_base_seconds:
            msg = "retry_max_seconds must be greater than or equal to retry_base_seconds"
            raise ValueError(msg)
        return self


class ModelSettings(BaseModel):
    """Configure the chat model used by agent graphs."""

    model_config = ConfigDict(extra="forbid")
    provider: ModelProvider = Field(default="bedrock")
    model_id: str = Field(default="anthropic.claude-sonnet-4-20250514-v1:0", min_length=1)
    region_name: str = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0)
    runtime: ModelRuntimeSettings = Field(default_factory=ModelRuntimeSettings)


class MCPServerSettings(BaseModel):
    """Configure one remote MCP server connection."""

    model_config = ConfigDict(extra="forbid")
    host: str = Field(min_length=1)
    port: int = Field(gt=0, le=65535)
    transport: Literal["streamable_http", "sse"] = Field(default="streamable_http")
    endpoint: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_url_format(self) -> Self:
        """Validate the computed MCP endpoint URL shape."""
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            msg = f"Invalid MCP server URL: {self.url}"
            raise ValueError(msg)
        return self

    @property
    def url(self) -> str:
        """Return the complete MCP endpoint URL."""
        endpoint = self.endpoint
        if endpoint is None:
            endpoint = "mcp/" if self.transport == "streamable_http" else "sse"
        return f"http://{self.host}:{self.port}/{endpoint.lstrip('/')}"


class MCPServersSettings(BaseModel):
    """Configure MCP services used by agent graphs."""

    model_config = ConfigDict(extra="forbid")
    wiki_service: MCPServerSettings = Field(
        default_factory=lambda: MCPServerSettings(host="wiki_service", port=8000)
    )
    news_service: MCPServerSettings = Field(
        default_factory=lambda: MCPServerSettings(
            host="news_service",
            port=8000,
            transport="sse",
        )
    )


class WorldBuilderSettings(BaseModel):
    """Configure the World Builder runtime limits."""

    model_config = ConfigDict(extra="forbid")
    max_steps: int = Field(default=8, gt=0)
    max_actors: int = Field(default=8, gt=0)
    max_state_files: int = Field(default=12, gt=0)


class AgentServiceConfig(BaseServiceConfig):
    """Validate agent_service runtime configuration."""

    service: ServiceSettings = Field(default_factory=ServiceSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    model: ModelSettings
    mcp_servers: MCPServersSettings = Field(default_factory=MCPServersSettings)
    world_builder: WorldBuilderSettings = Field(default_factory=WorldBuilderSettings)

    model_config = BaseServiceConfig.model_config | {"env_nested_delimiter": "__"}


@lru_cache
def get_config() -> AgentServiceConfig:
    """Load and cache the service configuration."""
    return AgentServiceConfig()
