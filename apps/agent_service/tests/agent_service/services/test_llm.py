"""Unit tests for LLM service configuration and model switching."""

import os
from collections.abc import Sequence
from unittest.mock import AsyncMock, patch

import pytest
from agent_service.models import ProviderErrorInfo
from agent_service.schema import (
    AgentServiceConfig,
    LangSmithSettings,
    ModelRuntimeSettings,
    ModelSettings,
    ObservabilitySettings,
)
from agent_service.services.llm import (
    LLMService,
    ProviderInvocationError,
    RetryingBoundModel,
    _calculate_retry_delay,
)
from botocore.exceptions import ClientError
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import ValidationError


class FakeBoundModel:
    """Raise prepared responses/errors from a deterministic async model."""

    def __init__(self, responses: list[BaseMessage | Exception]) -> None:
        self._responses = responses
        self.calls = 0

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> BaseMessage:
        assert messages
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _throttling_error() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Too many requests, please wait before trying again.",
            }
        },
        "Converse",
    )


RATE_LIMIT_MESSAGE = (
    "AWS Bedrock is rate-limiting the active model/profile. Retry this run in a moment."
)


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
            runtime=ModelRuntimeSettings(),
        ),
        observability=ObservabilitySettings(langsmith=LangSmithSettings(enabled=False)),
    )

    with patch.dict(os.environ, {}, clear=True):
        with patch("agent_service.services.llm.ChatBedrockConverse") as model_cls:
            service = LLMService.from_config(config)

        assert os.environ["LANGSMITH_TRACING"] == "false"

    assert hasattr(service.get_model(), "bind_tools")
    model_cls.assert_called_once_with(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="eu-central-1",
        temperature=0.1,
        max_tokens=2048,
    )
    assert service.model_info.model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
    assert service.model_info.provider == "aws_bedrock"


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

    assert hasattr(changed_model, "bind_tools")
    assert service.settings.model_id == "anthropic.claude-3-5-haiku-20241022-v1:0"
    assert service.settings.temperature == 0.4
    assert service.settings.max_tokens == 1024
    assert model_cls.call_args_list[-1].kwargs == {
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "region_name": "eu-central-1",
        "temperature": 0.4,
        "max_tokens": 1024,
    }


def test_llm_service_applies_langsmith_environment_when_enabled() -> None:
    """Verify LangSmith settings are exposed through process environment."""
    settings = ModelSettings(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="eu-central-1",
    )
    langsmith = LangSmithSettings(
        enabled=True,
        api_key="test-key",
        project="rozbirnyk-dev",
        endpoint="https://api.smith.langchain.com",
    )

    with patch.dict(os.environ, {}, clear=True):
        with patch("agent_service.services.llm.ChatBedrockConverse"):
            LLMService(settings, langsmith=langsmith)

        assert os.environ["LANGSMITH_TRACING"] == "true"
        assert os.environ["LANGSMITH_API_KEY"] == "test-key"
        assert os.environ["LANGSMITH_PROJECT"] == "rozbirnyk-dev"
        assert os.environ["LANGSMITH_ENDPOINT"] == "https://api.smith.langchain.com"


@pytest.mark.asyncio
async def test_retrying_bound_model_retries_bedrock_throttling_then_succeeds() -> None:
    """Verify throttling retries back off and eventually return a response."""
    runtime = ModelRuntimeSettings(
        min_seconds_between_calls=0.0,
        max_retries=2,
        retry_base_seconds=0.01,
        retry_max_seconds=0.01,
    )
    bound_model = RetryingBoundModel(
        provider="aws_bedrock",
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        runtime=runtime,
        gate=LLMService._get_bedrock_gate(runtime),
        model=FakeBoundModel(
            [
                _throttling_error(),
                AIMessage(content="done"),
            ]
        ),
    )

    with patch("agent_service.services.llm.asyncio.sleep", new_callable=AsyncMock) as sleep_mock:
        result = await bound_model.ainvoke([AIMessage(content="hello")])

    assert result.content == "done"
    sleep_mock.assert_called_once()


@pytest.mark.asyncio
async def test_retrying_bound_model_exhausts_throttling_retries() -> None:
    """Verify repeated throttling becomes a typed provider error."""
    runtime = ModelRuntimeSettings(
        min_seconds_between_calls=0.0,
        max_retries=1,
        retry_base_seconds=0.01,
        retry_max_seconds=0.01,
    )
    bound_model = RetryingBoundModel(
        provider="aws_bedrock",
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        runtime=runtime,
        gate=LLMService._get_bedrock_gate(runtime),
        model=FakeBoundModel(
            [
                _throttling_error(),
                _throttling_error(),
            ]
        ),
    )

    with patch("agent_service.services.llm.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(ProviderInvocationError) as error_info:
            await bound_model.ainvoke([AIMessage(content="hello")])

    typed_error = error_info.value.to_error_info()
    assert typed_error == ProviderErrorInfo(
        error_code="provider_rate_limited",
        message=RATE_LIMIT_MESSAGE,
        retryable=True,
        provider="aws_bedrock",
        details={
            "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
            "throttling_error_code": "ThrottlingException",
            "provider_message": "Too many requests, please wait before trying again.",
            "attempts": 2,
        },
    )


def test_retry_delay_stays_within_runtime_cap() -> None:
    """Verify jittered delay never exceeds the configured cap."""
    runtime = ModelRuntimeSettings(
        retry_base_seconds=1.0,
        retry_max_seconds=4.0,
    )

    delay = _calculate_retry_delay(runtime, attempt=4)

    assert 0.0 < delay <= 4.0
