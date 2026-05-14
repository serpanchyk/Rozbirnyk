"""Manage asynchronous World Builder runs in memory."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from agent_service.agents.world_builder import WorldBuilder
from agent_service.models import (
    ActiveModelInfo,
    ProviderErrorInfo,
    WikiFileSummary,
    WorldBuilderEventsResponse,
    WorldBuilderEventType,
    WorldBuilderLimits,
    WorldBuilderProgressEvent,
    WorldBuilderRunRequest,
    WorldBuilderRunResponse,
    WorldBuilderRunStatusResponse,
    WorldBuilderRunSummary,
    WorldBuilderStage,
    WorldBuilderStatus,
)
from agent_service.services.llm import ProviderInvocationError
from agent_service.tools.registry import ToolRegistry

type FileFetcher = Callable[[str], Awaitable[list[WikiFileSummary]]]


@dataclass(slots=True)
class RunRecord:
    """Carry mutable run state for one background execution."""

    run_id: str
    session_id: str
    scenario: str
    effective_limits: WorldBuilderLimits
    model: ActiveModelInfo
    status: WorldBuilderStatus = WorldBuilderStatus.QUEUED
    stage: WorldBuilderStage = WorldBuilderStage.QUEUED
    result_summary: WorldBuilderRunSummary | None = None
    error: str | None = None
    error_info: ProviderErrorInfo | None = None
    events: list[WorldBuilderProgressEvent] = field(default_factory=list)
    next_sequence: int = 1
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    task: asyncio.Task[None] | None = None

    def to_response(self) -> WorldBuilderRunStatusResponse:
        """Convert the record to an API response."""
        return WorldBuilderRunStatusResponse(
            run_id=self.run_id,
            session_id=self.session_id,
            status=self.status,
            stage=self.stage,
            effective_limits=self.effective_limits,
            result_summary=self.result_summary,
            error=self.error,
            error_info=self.error_info,
            model=self.model,
            updated_at=self.updated_at,
        )


class WorldBuilderRunManager:
    """Start, track, and validate World Builder runs."""

    def __init__(
        self,
        *,
        model: object,
        tool_registry: ToolRegistry,
        max_steps: int,
        hard_limits: WorldBuilderLimits,
        model_info: ActiveModelInfo,
        fetch_wiki_files: FileFetcher,
        tracing_enabled: bool = False,
    ) -> None:
        """Initialize the manager with runtime dependencies."""
        self._model = model
        self._tool_registry = tool_registry
        self._max_steps = max_steps
        self._hard_limits = hard_limits
        self._model_info = model_info
        self._fetch_wiki_files = fetch_wiki_files
        self._tracing_enabled = tracing_enabled
        self._runs: dict[str, RunRecord] = {}
        self._active_run_ids_by_session: dict[str, str] = {}

    async def start_run(self, request: WorldBuilderRunRequest) -> WorldBuilderRunResponse:
        """Start one background run for a session."""
        active_run_id = self._active_run_ids_by_session.get(request.session_id)
        if active_run_id is not None:
            active_run = self._runs[active_run_id]
            if active_run.status in {WorldBuilderStatus.QUEUED, WorldBuilderStatus.RUNNING}:
                msg = f"Session {request.session_id} already has an active World Builder run."
                raise ValueError(msg)

        run_id = uuid4().hex
        record = RunRecord(
            run_id=run_id,
            session_id=request.session_id,
            scenario=request.scenario,
            effective_limits=self._effective_limits(request),
            model=self._model_info,
        )
        self._runs[run_id] = record
        self._active_run_ids_by_session[request.session_id] = run_id
        self._emit_event(
            record,
            event=WorldBuilderEventType.STARTED,
            stage=WorldBuilderStage.QUEUED,
            message="World Builder run queued.",
        )
        record.task = asyncio.create_task(self._run(record), name=f"world-builder-{run_id}")
        return WorldBuilderRunResponse(
            run_id=run_id,
            session_id=request.session_id,
            status=record.status,
        )

    def get_status(self, run_id: str) -> WorldBuilderRunStatusResponse:
        """Return the current status for one run."""
        record = self._runs.get(run_id)
        if record is None:
            msg = f"Unknown World Builder run: {run_id}"
            raise KeyError(msg)
        return record.to_response()

    def get_status_for_session(self, session_id: str) -> WorldBuilderRunStatusResponse | None:
        """Return the current status for the session's most recent run."""
        run_id = self._active_run_ids_by_session.get(session_id)
        if run_id is None:
            return None
        return self._runs[run_id].to_response()

    def list_events_for_session(
        self,
        session_id: str,
        after_sequence: int = 0,
    ) -> WorldBuilderEventsResponse | None:
        """Return ordered events for the session's latest run."""
        run_id = self._active_run_ids_by_session.get(session_id)
        if run_id is None:
            return None
        record = self._runs[run_id]
        events = [event for event in record.events if event.sequence > after_sequence]
        return WorldBuilderEventsResponse(
            run_id=record.run_id,
            session_id=record.session_id,
            events=events,
        )

    def _effective_limits(self, request: WorldBuilderRunRequest) -> WorldBuilderLimits:
        return WorldBuilderLimits(
            max_actors=min(
                request.max_actors or self._hard_limits.max_actors,
                self._hard_limits.max_actors,
            ),
            max_state_files=min(
                request.max_state_files or self._hard_limits.max_state_files,
                self._hard_limits.max_state_files,
            ),
        )

    async def _run(self, record: RunRecord) -> None:
        try:
            self._update(
                record,
                status=WorldBuilderStatus.RUNNING,
                stage=WorldBuilderStage.RESEARCHING,
            )
            self._emit_event(
                record,
                event=WorldBuilderEventType.RESEARCHING,
                stage=WorldBuilderStage.RESEARCHING,
                message="World Builder is researching the scenario.",
            )
            builder = WorldBuilder(
                model=self._model,
                tool_registry=self._tool_registry,
                max_steps=self._max_steps,
            )
            graph = builder.create_graph()
            initial_state = builder.build_initial_state(
                scenario=record.scenario,
                session_id=record.session_id,
                max_actors=record.effective_limits.max_actors,
                max_state_files=record.effective_limits.max_state_files,
            )
            graph_run_config = self._build_graph_run_config(record)
            if graph_run_config is None:
                result = await graph.ainvoke(initial_state)
            else:
                result = await graph.ainvoke(initial_state, config=graph_run_config)
            self._update(record, stage=WorldBuilderStage.COLLECTING_SNAPSHOT)
            files = await self._fetch_wiki_files(record.session_id)
            self._emit_file_events(record, files)
            summary = self._build_summary(files, result.get("messages", []))
            self._validate_limits(record.effective_limits, summary)
            self._update(
                record,
                status=WorldBuilderStatus.COMPLETED,
                stage=WorldBuilderStage.COMPLETED,
                result_summary=summary,
            )
            self._emit_event(
                record,
                event=WorldBuilderEventType.COMPLETED,
                stage=WorldBuilderStage.COMPLETED,
                message=summary.completion_message or "World Builder completed successfully.",
            )
        except ProviderInvocationError as error:
            error_info = error.to_error_info()
            self._update(
                record,
                status=WorldBuilderStatus.FAILED,
                stage=WorldBuilderStage.FAILED,
                error=error.message,
                error_info=error_info,
            )
            self._emit_event(
                record,
                event=WorldBuilderEventType.FAILED,
                stage=WorldBuilderStage.FAILED,
                message=error.message,
                error_info=error_info,
            )
        except Exception as error:
            self._update(
                record,
                status=WorldBuilderStatus.FAILED,
                stage=WorldBuilderStage.FAILED,
                error=str(error),
            )
            self._emit_event(
                record,
                event=WorldBuilderEventType.FAILED,
                stage=WorldBuilderStage.FAILED,
                message=str(error),
            )

    def _build_summary(
        self,
        files: list[WikiFileSummary],
        messages: list[BaseMessage],
    ) -> WorldBuilderRunSummary:
        """Create a deterministic summary from wiki metadata and graph output."""
        state_files = [file for file in files if file.kind == "state"]
        actor_files = [file for file in files if file.kind == "actor"]
        completion_message: str | None = None
        if messages:
            content = getattr(messages[-1], "content", None)
            if isinstance(content, str):
                completion_message = content
        return WorldBuilderRunSummary(
            state_files=state_files,
            actor_files=actor_files,
            completion_message=completion_message,
        )

    def _validate_limits(
        self,
        limits: WorldBuilderLimits,
        summary: WorldBuilderRunSummary,
    ) -> None:
        if len(summary.actor_files) > limits.max_actors:
            msg = (
                f"World Builder created {len(summary.actor_files)} actor files, "
                f"exceeding the limit of {limits.max_actors}."
            )
            raise ValueError(msg)
        if len(summary.state_files) > limits.max_state_files:
            msg = (
                f"World Builder created {len(summary.state_files)} state files, "
                f"exceeding the limit of {limits.max_state_files}."
            )
            raise ValueError(msg)

    def _emit_file_events(self, record: RunRecord, files: list[WikiFileSummary]) -> None:
        """Emit one file-created event for each generated wiki file."""
        for file in files:
            if file.kind not in {"state", "actor"}:
                continue
            stage = (
                WorldBuilderStage.BUILDING_STATES
                if file.kind == "state"
                else WorldBuilderStage.BUILDING_ACTORS
            )
            self._emit_event(
                record,
                event=WorldBuilderEventType.FILE_CREATED,
                stage=stage,
                message=f"Created {file.kind} file {file.path}.",
                file=file,
            )

    def _emit_event(
        self,
        record: RunRecord,
        *,
        event: WorldBuilderEventType,
        stage: WorldBuilderStage,
        message: str,
        file: WikiFileSummary | None = None,
        error_info: ProviderErrorInfo | None = None,
    ) -> None:
        """Append one progress event to the run record."""
        progress_event = WorldBuilderProgressEvent(
            sequence=record.next_sequence,
            run_id=record.run_id,
            session_id=record.session_id,
            event=event,
            stage=stage,
            message=message,
            file=file,
            error_info=error_info,
            model=record.model,
        )
        record.events.append(progress_event)
        record.next_sequence += 1

    def _build_graph_run_config(self, record: RunRecord) -> RunnableConfig | None:
        """Build LangChain runnable config for traced World Builder executions."""
        if not self._tracing_enabled:
            return None
        return {
            "run_name": "world_builder",
            "tags": ["agent_service", "world_builder"],
            "metadata": {
                "session_id": record.session_id,
                "run_id": record.run_id,
                "max_actors": record.effective_limits.max_actors,
                "max_state_files": record.effective_limits.max_state_files,
            },
        }

    def _update(
        self,
        record: RunRecord,
        *,
        status: WorldBuilderStatus | None = None,
        stage: WorldBuilderStage | None = None,
        result_summary: WorldBuilderRunSummary | None = None,
        error: str | None = None,
        error_info: ProviderErrorInfo | None = None,
    ) -> None:
        if status is not None:
            record.status = status
        if stage is not None:
            record.stage = stage
        if result_summary is not None:
            record.result_summary = result_summary
        if error is not None:
            record.error = error
        if error_info is not None:
            record.error_info = error_info
        record.updated_at = datetime.now(UTC)
