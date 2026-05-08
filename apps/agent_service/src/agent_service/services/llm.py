"""Manage provider-backed chat models for agent graph execution."""

from typing import cast

from langchain_aws import ChatBedrockConverse

from agent_service.agents.base import ToolBindableModel
from agent_service.schema import AgentServiceConfig, ModelSettings


class LLMService:
    """Create and switch chat models without exposing providers to agents."""

    def __init__(self, settings: ModelSettings) -> None:
        """Initialize the service with validated model settings.

        Args:
            settings: Model configuration used to create the initial chat model.
        """
        self._settings = settings
        self._model = self._create_model(settings)

    @classmethod
    def from_config(cls, config: AgentServiceConfig) -> "LLMService":
        """Create an LLM service from the agent service configuration.

        Args:
            config: Agent service configuration.

        Returns:
            Service with the configured model already constructed.
        """
        return cls(config.model)

    @property
    def settings(self) -> ModelSettings:
        """Return the active model settings."""
        return self._settings

    def get_model(self) -> ToolBindableModel:
        """Return the active chat model for agent graph construction."""
        return self._model

    def change_model(
        self,
        settings: ModelSettings | None = None,
        *,
        model_id: str | None = None,
        region_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ToolBindableModel:
        """Switch the active model and return it.

        Args:
            settings: Complete replacement settings for the next model.
            model_id: Optional model identifier override.
            region_name: Optional provider region override.
            temperature: Optional sampling temperature override.
            max_tokens: Optional maximum output token override.

        Returns:
            The newly active chat model.
        """
        updates = {
            key: value
            for key, value in {
                "model_id": model_id,
                "region_name": region_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }.items()
            if value is not None
        }
        next_settings = settings
        if next_settings is None:
            next_settings = ModelSettings.model_validate(self._settings.model_dump() | updates)
        self._settings = next_settings
        self._model = self._create_model(next_settings)
        return self._model

    def _create_model(self, settings: ModelSettings) -> ToolBindableModel:
        """Create a provider-specific model behind the service boundary."""
        if settings.provider == "bedrock":
            return cast(
                ToolBindableModel,
                ChatBedrockConverse(
                    model_id=settings.model_id,
                    region_name=settings.region_name,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                ),
            )
        msg = f"Unsupported LLM provider: {settings.provider}"
        raise ValueError(msg)
