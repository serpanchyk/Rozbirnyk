"""Define API models for World Builder runs."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class WorldBuilderStage(StrEnum):
    """Represent coarse progress stages for a World Builder run."""

    QUEUED = "queued"
    RESEARCHING = "researching"
    BUILDING_STATES = "building_states"
    BUILDING_ACTORS = "building_actors"
    COLLECTING_SNAPSHOT = "collecting_snapshot"
    COMPLETED = "completed"
    FAILED = "failed"


class WorldBuilderStatus(StrEnum):
    """Represent terminal and in-flight run states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorldBuilderEventType(StrEnum):
    """Represent standardized World Builder progress events."""

    STARTED = "world_builder.started"
    RESEARCHING = "world_builder.researching"
    FILE_CREATED = "world_builder.file_created"
    COMPLETED = "world_builder.completed"
    FAILED = "world_builder.failed"


class WorldBuilderLimits(BaseModel):
    """Represent effective World Builder file limits."""

    model_config = ConfigDict(extra="forbid")
    max_actors: int = Field(gt=0)
    max_state_files: int = Field(gt=0)


class WorldBuilderRunRequest(BaseModel):
    """Start one World Builder run."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1)
    scenario: str = Field(min_length=1)
    max_actors: int | None = Field(default=None, gt=0)
    max_state_files: int | None = Field(default=None, gt=0)


class WikiFileSummary(BaseModel):
    """Summarize one wiki file returned by the wiki-service API."""

    model_config = ConfigDict(extra="forbid")
    path: str
    title: str
    short_description: str
    kind: str


class WorldBuilderRunSummary(BaseModel):
    """Summarize the completed run output."""

    model_config = ConfigDict(extra="forbid")
    state_files: list[WikiFileSummary] = Field(default_factory=list)
    actor_files: list[WikiFileSummary] = Field(default_factory=list)
    completion_message: str | None = None


class WorldBuilderRunResponse(BaseModel):
    """Return the run identity immediately after creation."""

    model_config = ConfigDict(extra="forbid")
    run_id: str
    session_id: str
    status: WorldBuilderStatus


class WorldBuilderProgressEvent(BaseModel):
    """Represent one progress event emitted during a World Builder run."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1)
    run_id: str
    session_id: str
    event: WorldBuilderEventType
    stage: WorldBuilderStage
    message: str
    file: WikiFileSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorldBuilderEventsResponse(BaseModel):
    """Return the accumulated progress events for a World Builder session."""

    model_config = ConfigDict(extra="forbid")
    run_id: str
    session_id: str
    events: list[WorldBuilderProgressEvent] = Field(default_factory=list)


class WorldBuilderRunStatusResponse(BaseModel):
    """Return the current status for a World Builder run."""

    model_config = ConfigDict(extra="forbid")
    run_id: str
    session_id: str
    status: WorldBuilderStatus
    stage: WorldBuilderStage
    effective_limits: WorldBuilderLimits
    result_summary: WorldBuilderRunSummary | None = None
    error: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
