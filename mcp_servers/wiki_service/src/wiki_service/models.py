"""Define API models for Wiki Service responses and requests."""

from pydantic import BaseModel, ConfigDict, Field


class SessionRequest(BaseModel):
    """Represent a request scoped to a wiki session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(default="default")


class TimelineResponse(BaseModel):
    """Represent timeline content for a wiki session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    content: str


class WikiFileMetadata(BaseModel):
    """Represent title and description metadata for a wiki file."""

    model_config = ConfigDict(extra="forbid")
    path: str
    title: str
    short_description: str
    kind: str


class WikiFilesResponse(BaseModel):
    """Represent metadata for all files in a wiki session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    files: list[WikiFileMetadata]


class ActorFilesResponse(BaseModel):
    """Represent actor-specific context files for agent injection."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    actor_id: str
    files: list[WikiFileMetadata]
    contents: dict[str, str]


class ResetResponse(BaseModel):
    """Represent the result of resetting a wiki session."""

    model_config = ConfigDict(extra="forbid")
    session_id: str
    message: str
