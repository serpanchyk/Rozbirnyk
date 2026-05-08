"""Unit tests for LLM service configuration and model switching."""

from unittest.mock import patch

import pytest
from agent_service.schema import AgentServiceConfig, ModelSettings
from agent_service.services.llm import LLMService
from pydantic import ValidationError


def test_model_region_name_is_required() -> None:
    """Verify Bedrock region configuration fails fast when absent."""
    with pytest.raises(ValidationError):
        ModelSettings.model_validate({})


def test_llm_service_creates_configured_model() -> None:
    """Verify model settings flow into the provider constructor."""
    config = AgentServiceConfig(
        model=ModelSettings(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="eu-central-1",
            temperature=0.1,
            max_tokens=2048,
        )
    )

    with patch("agent_service.services.llm.ChatBedrockConverse") as model_cls:
        service = LLMService.from_config(config)

    assert service.get_model() == model_cls.return_value
    model_cls.assert_called_once_with(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="eu-central-1",
        temperature=0.1,
        max_tokens=2048,
    )


def test_llm_service_changes_models_without_agent_involvement() -> None:
    """Verify model changes are handled inside the service boundary."""
    settings = ModelSettings(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="eu-central-1",
    )

    with patch("agent_service.services.llm.ChatBedrockConverse") as model_cls:
        service = LLMService(settings)
        changed_model = service.change_model(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
            temperature=0.4,
            max_tokens=1024,
        )

    assert changed_model == model_cls.return_value
    assert service.settings.model_id == "anthropic.claude-3-5-haiku-20241022-v1:0"
    assert service.settings.temperature == 0.4
    assert service.settings.max_tokens == 1024
    assert model_cls.call_args_list[-1].kwargs == {
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "region_name": "eu-central-1",
        "temperature": 0.4,
        "max_tokens": 1024,
    }
