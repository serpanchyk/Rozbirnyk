"""Unit tests for Bedrock model configuration."""

from unittest.mock import patch

import pytest
from agent_service.models.bedrock import create_bedrock_model
from agent_service.schema import AgentServiceConfig, ModelSettings
from pydantic import ValidationError


def test_model_region_name_is_required() -> None:
    """Verify Bedrock region configuration fails fast when absent."""
    with pytest.raises(ValidationError):
        ModelSettings.model_validate({})


def test_bedrock_model_factory_passes_configured_values() -> None:
    """Verify model settings flow into ChatBedrockConverse without AWS calls."""
    config = AgentServiceConfig(
        model=ModelSettings(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="eu-central-1",
            temperature=0.1,
            max_tokens=2048,
        )
    )

    with patch("agent_service.models.bedrock.ChatBedrockConverse") as model_cls:
        result = create_bedrock_model(config)

    assert result == model_cls.return_value
    model_cls.assert_called_once_with(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="eu-central-1",
        temperature=0.1,
        max_tokens=2048,
    )
