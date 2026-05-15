"""Manage provider-backed chat models for agent graph execution."""

import asyncio
import os
import random
from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic
from typing import cast

from botocore.exceptions import ClientError
from common.logging import setup_logger
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from agent_service.agents.base import AsyncMessageModel, ToolBindableModel
from agent_service.models import ActiveModelInfo, ProviderErrorInfo
from agent_service.schema import (
    AgentServiceConfig,
    LangSmithSettings,
    ModelRuntimeSettings,
    ModelSettings,
)

logger = setup_logger("agent_service.llm")


@dataclass(slots=True)
class BedrockThrottlingDetails:
    """Describe a throttling failure detected in the Bedrock call chain."""

    error_code: str
    provider_message: str


class ProviderInvocationError(Exception):
    """Represent a typed provider failure raised from the LLM boundary."""

    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        retryable: bool,
        provider: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.retryable = retryable
        self.provider = provider
        self.details = details

    def to_error_info(self) -> ProviderErrorInfo:
        """Convert the exception into the API error payload."""
        return ProviderErrorInfo(
            error_code=self.error_code,
            message=self.message,
            retryable=self.retryable,
            provider=self.provider,
            details=self.details,
        )


class BedrockRequestGate:
    """Serialize and pace outbound Bedrock requests inside one process."""

    def __init__(self, runtime: ModelRuntimeSettings) -> None:
        self._runtime = runtime
        self._semaphore = asyncio.Semaphore(runtime.max_concurrency)
        self._pacing_lock = asyncio.Lock()
        self._next_request_at = 0.0

    async def __aenter__(self) -> None:
        await self._semaphore.acquire()
        try:
            await self._wait_for_spacing()
        except Exception:
            self._semaphore.release()
            raise
        return None

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._semaphore.release()

    async def _wait_for_spacing(self) -> None:
        async with self._pacing_lock:
            now = monotonic()
            if self._next_request_at > now:
                await asyncio.sleep(self._next_request_at - now)
            self._next_request_at = monotonic() + self._runtime.min_seconds_between_calls


class RetryingBoundModel(AsyncMessageModel):
    """Wrap a bound Bedrock model with process-local gating and retry behavior."""

    def __init__(
        self,
        *,
        provider: str,
        model_id: str,
        runtime: ModelRuntimeSettings,
        gate: BedrockRequestGate,
        model: AsyncMessageModel,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._runtime = runtime
        self._gate = gate
        self._model = model

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> BaseMessage:
        """Invoke the underlying model with Bedrock-aware retries."""
        attempt = 0
        while True:
            try:
                async with self._gate:
                    return await self._model.ainvoke(messages)
            except Exception as error:
                throttling = _extract_bedrock_throttling(error)
                if throttling is None:
                    raise
                if attempt >= self._runtime.max_retries:
                    logger.error(
                        "Bedrock throttling retries exhausted.",
                        extra={
                            "provider": self._provider,
                            "model_id": self._model_id,
                            "attempts": attempt + 1,
                            "max_retries": self._runtime.max_retries,
                            "throttling_error_code": throttling.error_code,
                            "provider_message": throttling.provider_message,
                        },
                    )
                    raise ProviderInvocationError(
                        error_code="provider_rate_limited",
                        message=(
                            "AWS Bedrock is rate-limiting the active model/profile. "
                            "Retry this run in a moment."
                        ),
                        retryable=True,
                        provider="aws_bedrock",
                        details={
                            "model_id": self._model_id,
                            "throttling_error_code": throttling.error_code,
                            "provider_message": throttling.provider_message,
                            "attempts": attempt + 1,
                        },
                    ) from error
                delay_seconds = _calculate_retry_delay(self._runtime, attempt)
                logger.warning(
                    "Bedrock throttled model invocation; retrying.",
                    extra={
                        "provider": self._provider,
                        "model_id": self._model_id,
                        "attempt": attempt + 1,
                        "max_retries": self._runtime.max_retries,
                        "delay_seconds": delay_seconds,
                        "throttling_error_code": throttling.error_code,
                    },
                )
                await asyncio.sleep(delay_seconds)
                attempt += 1


class RetryingToolBindableModel(ToolBindableModel):
    """Wrap a provider model so every bound invocation uses retries and pacing."""

    def __init__(
        self,
        *,
        provider: str,
        model_id: str,
        runtime: ModelRuntimeSettings,
        gate: BedrockRequestGate,
        model: ToolBindableModel,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._runtime = runtime
        self._gate = gate
        self._model = model

    def bind_tools(self, tools: Sequence[BaseTool]) -> AsyncMessageModel:
        return RetryingBoundModel(
            provider=self._provider,
            model_id=self._model_id,
            runtime=self._runtime,
            gate=self._gate,
            model=self._model.bind_tools(tools),
        )


class LLMService:
    """Create and switch chat models without exposing providers to agents."""

    _bedrock_gate: BedrockRequestGate | None = None
    _bedrock_gate_settings: tuple[int, float] | None = None

    def __init__(
        self,
        settings: ModelSettings,
        langsmith: LangSmithSettings | None = None,
    ) -> None:
        """Initialize the service with validated model settings.

        Args:
            settings: Model configuration used to create the initial chat model.
            langsmith: Optional tracing configuration applied process-wide.
        """
        self._settings = settings
        self._langsmith = langsmith or LangSmithSettings()
        self._configure_langsmith_environment()
        self._model = self._create_model(settings)

    @classmethod
    def from_config(cls, config: AgentServiceConfig) -> "LLMService":
        """Create an LLM service from the agent service configuration."""
        return cls(config.model, langsmith=config.observability.langsmith)

    @property
    def settings(self) -> ModelSettings:
        """Return the active model settings."""
        return self._settings

    @property
    def model_info(self) -> ActiveModelInfo:
        """Return the active provider/model metadata exposed in API status."""
        provider = (
            "aws_bedrock" if self._settings.provider == "bedrock" else self._settings.provider
        )
        return ActiveModelInfo(
            provider=provider,
            model_id=self._settings.model_id,
            display_name=f"{provider}:{self._settings.model_id}",
        )

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
        """Switch the active model and return it."""
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
            logger.info(
                "Initializing AWS Bedrock model runtime.",
                extra={
                    "provider": "aws_bedrock",
                    "model_id": settings.model_id,
                    "region_name": settings.region_name,
                    "max_concurrency": settings.runtime.max_concurrency,
                    "min_seconds_between_calls": settings.runtime.min_seconds_between_calls,
                    "max_retries": settings.runtime.max_retries,
                    "retry_base_seconds": settings.runtime.retry_base_seconds,
                    "retry_max_seconds": settings.runtime.retry_max_seconds,
                },
            )
            model = cast(
                ToolBindableModel,
                ChatBedrockConverse(
                    model_id=settings.model_id,
                    region_name=settings.region_name,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                ),
            )
            return RetryingToolBindableModel(
                provider="aws_bedrock",
                model_id=settings.model_id,
                runtime=settings.runtime,
                gate=self._get_bedrock_gate(settings.runtime),
                model=model,
            )
        msg = f"Unsupported LLM provider: {settings.provider}"
        raise ValueError(msg)

    @classmethod
    def _get_bedrock_gate(cls, runtime: ModelRuntimeSettings) -> BedrockRequestGate:
        signature = (runtime.max_concurrency, runtime.min_seconds_between_calls)
        if cls._bedrock_gate is None or cls._bedrock_gate_settings != signature:
            cls._bedrock_gate = BedrockRequestGate(runtime)
            cls._bedrock_gate_settings = signature
        return cls._bedrock_gate

    def _configure_langsmith_environment(self) -> None:
        """Apply LangSmith tracing settings for LangChain and LangGraph runtimes."""
        os.environ["LANGSMITH_TRACING"] = "true" if self._langsmith.enabled else "false"
        if self._langsmith.api_key:
            os.environ["LANGSMITH_API_KEY"] = self._langsmith.api_key
        if self._langsmith.project:
            os.environ["LANGSMITH_PROJECT"] = self._langsmith.project
        if self._langsmith.endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = self._langsmith.endpoint


def _calculate_retry_delay(runtime: ModelRuntimeSettings, attempt: int) -> float:
    max_seconds = float(runtime.retry_max_seconds)
    base_seconds = float(runtime.retry_base_seconds)
    capped_base = min(max_seconds, base_seconds * float(2**attempt))
    delay = capped_base + random.uniform(0.0, base_seconds)
    if delay > max_seconds:
        return max_seconds
    return delay


def _extract_bedrock_throttling(error: BaseException) -> BedrockThrottlingDetails | None:
    visited: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, ClientError):
            code = str(current.response.get("Error", {}).get("Code", ""))
            message = str(current.response.get("Error", {}).get("Message", current))
            if _is_throttling_code(code) or _looks_like_rate_limit_message(message):
                return BedrockThrottlingDetails(
                    error_code=code or "ThrottlingException",
                    provider_message=message,
                )
        code_value = getattr(current, "code", None)
        if isinstance(code_value, str) and _is_throttling_code(code_value):
            return BedrockThrottlingDetails(
                error_code=code_value,
                provider_message=str(current),
            )
        message = str(current)
        if _looks_like_rate_limit_message(message):
            return BedrockThrottlingDetails(
                error_code="ThrottlingException",
                provider_message=message,
            )
        next_error = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        current = next_error if isinstance(next_error, BaseException) else None
    return None


def _is_throttling_code(error_code: str) -> bool:
    normalized = error_code.lower()
    return "throttl" in normalized or normalized in {
        "toomanyrequestsexception",
        "ratelimitexceeded",
    }


def _looks_like_rate_limit_message(message: str) -> bool:
    normalized = message.lower()
    return "throttlingexception" in normalized or "too many requests" in normalized
