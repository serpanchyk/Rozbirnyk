"""Expose the agent-service API for World Builder orchestration."""

import asyncio
import os
from typing import cast

import httpx
import uvicorn
from botocore.exceptions import BotoCoreError, ProfileNotFound
from botocore.session import get_session
from common.logging import setup_logger
from fastapi import FastAPI, HTTPException

from agent_service.models import (
    WikiFileSummary,
    WorldBuilderEventsResponse,
    WorldBuilderLimits,
    WorldBuilderRunRequest,
    WorldBuilderRunResponse,
    WorldBuilderRunStatusResponse,
)
from agent_service.run_manager import WorldBuilderRunManager
from agent_service.schema import AgentServiceConfig, get_config
from agent_service.services.llm import LLMService
from agent_service.tools.registry import ToolRegistry

logger = setup_logger("agent_service")


class WikiServiceClient:
    """Fetch wiki metadata from the wiki-service API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def list_files(self, session_id: str) -> list[WikiFileSummary]:
        """Return file metadata for one session."""
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.get("/api/v1/wiki/files", params={"session_id": session_id})
            response.raise_for_status()
        payload = response.json()
        return [WikiFileSummary.model_validate(item) for item in payload["files"]]


def create_app(
    *,
    run_manager: WorldBuilderRunManager | None = None,
) -> FastAPI:
    """Create the FastAPI application."""
    if run_manager is None:
        msg = "create_app requires a preconfigured WorldBuilderRunManager."
        raise TypeError(msg)
    app = FastAPI(title="Rozbirnyk Agent Service")
    app.state.run_manager = run_manager

    @app.post("/api/v1/world-builder/runs")
    async def start_world_builder_run(
        request: WorldBuilderRunRequest,
    ) -> WorldBuilderRunResponse:
        """Start one World Builder run."""
        try:
            return cast(WorldBuilderRunResponse, await app.state.run_manager.start_run(request))
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/v1/world-builder/runs/{run_id}")
    async def get_world_builder_run(run_id: str) -> WorldBuilderRunStatusResponse:
        """Return one World Builder run."""
        try:
            return cast(WorldBuilderRunStatusResponse, app.state.run_manager.get_status(run_id))
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/api/v1/world-builder/sessions/{session_id}")
    async def get_world_builder_session(session_id: str) -> WorldBuilderRunStatusResponse:
        """Return the latest World Builder run for a session."""
        status = app.state.run_manager.get_status_for_session(session_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"No World Builder run for {session_id}.")
        return cast(WorldBuilderRunStatusResponse, status)

    @app.get("/api/v1/world-builder/sessions/{session_id}/events")
    async def get_world_builder_session_events(
        session_id: str,
        after_sequence: int = 0,
    ) -> WorldBuilderEventsResponse:
        """Return the latest World Builder events for a session."""
        events = app.state.run_manager.list_events_for_session(
            session_id,
            after_sequence=after_sequence,
        )
        if events is None:
            raise HTTPException(status_code=404, detail=f"No World Builder run for {session_id}.")
        return cast(WorldBuilderEventsResponse, events)

    return app


def _build_run_manager(config: AgentServiceConfig) -> WorldBuilderRunManager:
    """Construct the real run manager from service configuration."""
    llm_service = LLMService.from_config(config)
    tool_registry = asyncio.run(ToolRegistry.discover(config.mcp_servers))
    wiki_client = WikiServiceClient(
        config.mcp_servers.wiki_service.url.rsplit("/mcp", maxsplit=1)[0]
    )
    return WorldBuilderRunManager(
        model=llm_service.get_model(),
        tool_registry=tool_registry,
        max_steps=config.world_builder.max_steps,
        hard_limits=WorldBuilderLimits(
            max_actors=config.world_builder.max_actors,
            max_state_files=config.world_builder.max_state_files,
        ),
        model_info=llm_service.model_info,
        fetch_wiki_files=wiki_client.list_files,
        tracing_enabled=config.observability.langsmith.enabled,
    )


def _validate_aws_credentials() -> None:
    """Fail fast when AWS credentials cannot be resolved for Bedrock startup."""
    try:
        credentials = get_session().get_credentials()
    except ProfileNotFound as error:
        profile = os.environ.get("AWS_PROFILE", "<unknown>")
        msg = (
            "AWS credentials could not be resolved for agent_service startup. "
            f"The configured AWS profile '{profile}' was not found."
        )
        raise RuntimeError(msg) from error
    except BotoCoreError as error:
        msg = (
            "AWS credentials could not be resolved for agent_service startup. "
            "Configure aws configure, AWS_PROFILE, direct AWS credential environment "
            "variables, or an IAM role."
        )
        raise RuntimeError(msg) from error

    if credentials is None:
        msg = (
            "AWS credentials could not be resolved for agent_service startup. "
            "Configure aws configure, AWS_PROFILE, direct AWS credential environment "
            "variables, or an IAM role."
        )
        raise RuntimeError(msg)

    try:
        credentials.get_frozen_credentials()
    except BotoCoreError as error:
        msg = "AWS credentials were discovered but could not be loaded for agent_service startup."
        raise RuntimeError(msg) from error


def _validate_startup_prereqs(config: AgentServiceConfig) -> None:
    """Validate runtime prerequisites that are outside static config parsing."""
    if config.model.provider == "bedrock":
        _validate_aws_credentials()


def main(config: AgentServiceConfig | None = None) -> None:
    """Run the service with the configured dependencies."""
    resolved_config = config or get_config()
    _validate_startup_prereqs(resolved_config)
    app = create_app(run_manager=_build_run_manager(resolved_config))
    uvicorn.run(app, host="0.0.0.0", port=resolved_config.service.port)


if __name__ == "__main__":
    config = get_config()
    logger.info(
        "Initializing Agent Service",
        extra={"host": "0.0.0.0", "port": config.service.port},
    )
    main(config)
