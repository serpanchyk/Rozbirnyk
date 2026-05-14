"""Define backend API models for simulation sessions."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(StrEnum):
    """Represent backend session state."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BuilderStage(StrEnum):
    """Mirror the coarse builder stages exposed by agent-service."""

    QUEUED = "queued"
    RESEARCHING = "researching"
    BUILDING_STATES = "building_states"
    BUILDING_ACTORS = "building_actors"
    COLLECTING_SNAPSHOT = "collecting_snapshot"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionEventType(StrEnum):
    """Represent frontend-visible World Builder event types."""

    STARTED = "world_builder.started"
    RESEARCHING = "world_builder.researching"
    FILE_CREATED = "world_builder.file_created"
    COMPLETED = "world_builder.completed"
    FAILED = "world_builder.failed"


class SessionLimits(BaseModel):
    """Carry optional session-level World Builder limits."""

    model_config = ConfigDict(extra="forbid")
    max_actors: int | None = Field(default=None, gt=0)
    max_state_files: int | None = Field(default=None, gt=0)


class WikiFileSummary(BaseModel):
    """Summarize one file in the session wiki."""

    model_config = ConfigDict(extra="forbid")
    path: str
    title: str
    short_description: str
    kind: str


class ProviderErrorInfo(BaseModel):
    """Carry a typed upstream provider failure for frontend handling."""

    model_config = ConfigDict(extra="forbid")
    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool
    provider: str = Field(min_length=1)
    details: dict[str, Any] | None = None


class ActiveModelInfo(BaseModel):
    """Describe the upstream provider/model used by the builder run."""

    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    display_name: str | None = None


class CreateSessionRequest(SessionLimits):
    """Create a simulation session."""

    scenario: str = Field(min_length=1)


class CreateSessionResponse(BaseModel):
    """Return the created session identity."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    scenario: str
    status: SessionStatus
    requested_limits: SessionLimits


class StartWorldBuilderResponse(BaseModel):
    """Return backend acknowledgement for a started builder run."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    run_id: str
    status: SessionStatus


class SessionStatusResponse(BaseModel):
    """Return the current session state plus built wiki snapshot."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    scenario: str
    status: SessionStatus
    stage: BuilderStage | None = None
    run_id: str | None = None
    requested_limits: SessionLimits
    effective_limits: SessionLimits | None = None
    error: str | None = None
    error_info: ProviderErrorInfo | None = None
    model: ActiveModelInfo | None = None
    state_files: list[WikiFileSummary] = Field(default_factory=list)
    actor_files: list[WikiFileSummary] = Field(default_factory=list)


class SessionEvent(BaseModel):
    """Represent one backend session progress event."""

    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1)
    run_id: str
    session_id: str
    event: SessionEventType
    stage: BuilderStage
    message: str
    file: WikiFileSummary | None = None
    error_info: ProviderErrorInfo | None = None
    model: ActiveModelInfo | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionEventsResponse(BaseModel):
    """Return ordered World Builder events for one session."""

    model_config = ConfigDict(extra="forbid")
    run_id: str
    session_id: str
    events: list[SessionEvent] = Field(default_factory=list)
