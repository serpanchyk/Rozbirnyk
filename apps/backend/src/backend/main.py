"""Expose the backend API for simulation session orchestration."""

import asyncio
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

import httpx
import uvicorn
from common.logging import setup_logger
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.models import (
    ActiveModelInfo,
    BuilderStage,
    CreateSessionRequest,
    CreateSessionResponse,
    ProviderErrorInfo,
    SessionEvent,
    SessionEventsResponse,
    SessionLimits,
    SessionStatus,
    SessionStatusResponse,
    StartWorldBuilderResponse,
    WikiFileSummary,
)
from backend.schema import BackendConfig, get_config

logger = setup_logger("backend")


class WikiServiceClient:
    """Call the wiki-service API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def reset(self, session_id: str) -> None:
        """Reset one wiki session."""
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.post("/api/v1/wiki/reset", json={"session_id": session_id})
            response.raise_for_status()

    async def list_files(self, session_id: str) -> list[WikiFileSummary]:
        """List files for one session."""
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.get("/api/v1/wiki/files", params={"session_id": session_id})
            response.raise_for_status()
        payload = response.json()
        return [WikiFileSummary.model_validate(item) for item in payload["files"]]


class AgentServiceClient:
    """Call the agent-service API."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def start_world_builder(
        self,
        session_id: str,
        scenario: str,
        limits: SessionLimits,
    ) -> dict[str, object]:
        """Start one World Builder run."""
        payload: dict[str, object] = {"session_id": session_id, "scenario": scenario}
        if limits.max_actors is not None:
            payload["max_actors"] = limits.max_actors
        if limits.max_state_files is not None:
            payload["max_state_files"] = limits.max_state_files
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.post("/api/v1/world-builder/runs", json=payload)
            response.raise_for_status()
        return cast(dict[str, object], response.json())

    async def get_world_builder_session(self, session_id: str) -> dict[str, object]:
        """Return the latest builder status for one session."""
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.get(f"/api/v1/world-builder/sessions/{session_id}")
            response.raise_for_status()
        return cast(dict[str, object], response.json())

    async def get_world_builder_session_events(
        self,
        session_id: str,
        after_sequence: int,
    ) -> SessionEventsResponse:
        """Return the latest builder events for one session."""
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            response = await client.get(
                f"/api/v1/world-builder/sessions/{session_id}/events",
                params={"after_sequence": after_sequence},
            )
            response.raise_for_status()
        return SessionEventsResponse.model_validate(response.json())


@dataclass(slots=True)
class SessionRecord:
    """Carry in-memory session state."""

    session_id: str
    scenario: str
    requested_limits: SessionLimits
    status: SessionStatus = SessionStatus.CREATED
    stage: BuilderStage | None = None
    run_id: str | None = None
    effective_limits: SessionLimits | None = None
    error: str | None = None
    error_info: ProviderErrorInfo | None = None
    model: ActiveModelInfo | None = None


class SessionStore:
    """Store sessions in memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionRecord] = {}

    def create(self, request: CreateSessionRequest) -> SessionRecord:
        """Create and store one session record."""
        session_id = uuid4().hex
        record = SessionRecord(
            session_id=session_id,
            scenario=request.scenario,
            requested_limits=SessionLimits(
                max_actors=request.max_actors,
                max_state_files=request.max_state_files,
            ),
        )
        self._sessions[session_id] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        """Return one session record."""
        record = self._sessions.get(session_id)
        if record is None:
            msg = f"Unknown session: {session_id}"
            raise KeyError(msg)
        return record


def _map_session_status(raw_status: str) -> SessionStatus:
    if raw_status == "queued":
        return SessionStatus.QUEUED
    if raw_status == "running":
        return SessionStatus.RUNNING
    if raw_status == "completed":
        return SessionStatus.COMPLETED
    if raw_status == "failed":
        return SessionStatus.FAILED
    msg = f"Unknown builder status: {raw_status}"
    raise ValueError(msg)


def create_app(
    *,
    session_store: SessionStore | None = None,
    agent_client: AgentServiceClient | None = None,
    wiki_client: WikiServiceClient | None = None,
) -> FastAPI:
    """Create the backend FastAPI application."""
    config: BackendConfig = get_config()
    resolved_store = session_store or SessionStore()
    resolved_agent_client = agent_client or AgentServiceClient(config.upstream.agent_service_url)
    resolved_wiki_client = wiki_client or WikiServiceClient(config.upstream.wiki_service_url)

    app = FastAPI(title="Rozbirnyk Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.upstream.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.sessions = resolved_store
    app.state.agent_client = resolved_agent_client
    app.state.wiki_client = resolved_wiki_client

    @app.post("/api/v1/sessions")
    async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
        """Create one simulation session and reset its wiki."""
        record = app.state.sessions.create(request)
        try:
            await app.state.wiki_client.reset(record.session_id)
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        return CreateSessionResponse(
            session_id=record.session_id,
            scenario=record.scenario,
            status=record.status,
            requested_limits=record.requested_limits,
        )

    @app.post("/api/v1/sessions/{session_id}/world-builder")
    async def start_world_builder(session_id: str) -> StartWorldBuilderResponse:
        """Start the World Builder for an existing session."""
        try:
            record = app.state.sessions.get(session_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        try:
            payload = await app.state.agent_client.start_world_builder(
                session_id=record.session_id,
                scenario=record.scenario,
                limits=record.requested_limits,
            )
        except httpx.HTTPStatusError as error:
            status_code = 409 if error.response.status_code == 409 else 502
            raise HTTPException(status_code=status_code, detail=error.response.text) from error
        except httpx.HTTPError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

        record.run_id = str(payload["run_id"])
        record.status = _map_session_status(str(payload["status"]))
        record.stage = BuilderStage.QUEUED
        return StartWorldBuilderResponse(
            session_id=record.session_id,
            run_id=record.run_id,
            status=record.status,
        )

    @app.get("/api/v1/sessions/{session_id}")
    async def get_session(session_id: str) -> SessionStatusResponse:
        """Return the latest session and World Builder state."""
        try:
            record = app.state.sessions.get(session_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        state_files: list[WikiFileSummary] = []
        actor_files: list[WikiFileSummary] = []
        if record.run_id is not None:
            try:
                payload = await app.state.agent_client.get_world_builder_session(session_id)
            except httpx.HTTPError as error:
                raise HTTPException(status_code=502, detail=str(error)) from error
            record.status = _map_session_status(str(payload["status"]))
            record.stage = BuilderStage(str(payload["stage"]))
            limits_payload = payload.get("effective_limits")
            if isinstance(limits_payload, dict):
                record.effective_limits = SessionLimits.model_validate(limits_payload)
            error_message = payload.get("error")
            record.error = str(error_message) if error_message else None
            error_info_payload = payload.get("error_info")
            record.error_info = (
                ProviderErrorInfo.model_validate(error_info_payload)
                if isinstance(error_info_payload, dict)
                else None
            )
            model_payload = payload.get("model")
            record.model = (
                ActiveModelInfo.model_validate(model_payload)
                if isinstance(model_payload, dict)
                else None
            )
            if record.status == SessionStatus.COMPLETED:
                files = await app.state.wiki_client.list_files(session_id)
                state_files = [file for file in files if file.kind == "state"]
                actor_files = [file for file in files if file.kind == "actor"]

        return SessionStatusResponse(
            session_id=record.session_id,
            scenario=record.scenario,
            status=record.status,
            stage=record.stage,
            run_id=record.run_id,
            requested_limits=record.requested_limits,
            effective_limits=record.effective_limits,
            error=record.error,
            error_info=record.error_info,
            model=record.model,
            state_files=state_files,
            actor_files=actor_files,
        )

    @app.get("/api/v1/sessions/{session_id}/events")
    async def get_session_events(session_id: str) -> StreamingResponse:
        """Stream World Builder events for one session over SSE."""
        try:
            record = app.state.sessions.get(session_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        if record.run_id is None:
            raise HTTPException(
                status_code=409,
                detail=f"Session {session_id} has no World Builder run yet.",
            )

        async def event_stream() -> AsyncGenerator[str, None]:
            last_sequence = 0
            while True:
                try:
                    response = await app.state.agent_client.get_world_builder_session_events(
                        session_id,
                        after_sequence=last_sequence,
                    )
                except httpx.HTTPError as error:
                    error_event = SessionEvent(
                        sequence=last_sequence + 1,
                        run_id=record.run_id or "unknown",
                        session_id=session_id,
                        event="world_builder.failed",
                        stage=BuilderStage.FAILED,
                        message=str(error),
                        model=record.model,
                    )
                    yield _format_sse_event(error_event)
                    return

                for event in response.events:
                    last_sequence = event.sequence
                    yield _format_sse_event(event)
                    if event.event.value in {
                        "world_builder.completed",
                        "world_builder.failed",
                    }:
                        return

                await asyncio.sleep(0.5)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return app


def _format_sse_event(event: SessionEvent) -> str:
    """Render one session event as an SSE payload."""
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event.value}\n"
        f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
    )


def main() -> None:
    """Run the backend service."""
    config = get_config()
    uvicorn.run(create_app(), host="0.0.0.0", port=config.service.port)


if __name__ == "__main__":
    logger.info(
        "Initializing Backend",
        extra={"host": "0.0.0.0", "port": get_config().service.port},
    )
    main()
