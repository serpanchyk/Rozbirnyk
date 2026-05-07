"""Expose the Wiki Service API and MCP tools for simulation state.

Data Flow: Agent or API Request -> Shared WikiManager -> Markdown Session Files
-> API Response or MCP Tool Result.

Logging Context: Emits structured service startup logs and relies on shared
context variables for trace, session, and user identifiers.

Async Behavior: FastAPI routes and MCP tools call asynchronous manager methods
that delegate blocking filesystem operations to worker threads.
"""

import uvicorn
from common.logging import setup_logger
from fastapi import FastAPI, HTTPException, Response
from fastmcp import FastMCP

from wiki_service.manager import DEFAULT_SESSION_ID, WikiManager
from wiki_service.models import (
    ActorFilesResponse,
    ResetResponse,
    SessionRequest,
    TimelineResponse,
    WikiFilesResponse,
)
from wiki_service.schema import get_config

logger = setup_logger("wiki_service")
config = get_config()
manager = WikiManager(config.storage.root_dir)
mcp = FastMCP("Rozbirnyk Wiki Service")


def _handle_error(error: Exception) -> HTTPException:
    """Convert domain exceptions into HTTP exceptions.

    Args:
        error: Exception raised by the WikiManager.

    Returns:
        HTTPException with a status code suitable for API clients.
    """
    if isinstance(error, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ValueError):
        return HTTPException(status_code=400, detail=str(error))
    return HTTPException(status_code=500, detail="Unexpected wiki service error.")


def create_app(wiki_manager: WikiManager) -> FastAPI:
    """Create the ASGI application for the Wiki Service.

    Args:
        wiki_manager: Shared manager used by API routes.

    Returns:
        FastAPI application with API routes and mounted MCP transport.
    """
    mcp_app = mcp.http_app(path="/", transport="http")
    app = FastAPI(title="Rozbirnyk Wiki Service", lifespan=mcp_app.lifespan)

    @app.post("/api/v1/wiki/reset")
    async def reset_wiki(request: SessionRequest) -> ResetResponse:
        """Reset one wiki session to an empty initialized structure."""
        try:
            await wiki_manager.reset(request.session_id)
        except Exception as error:
            raise _handle_error(error) from error
        return ResetResponse(session_id=request.session_id, message="Wiki session reset.")

    @app.get("/api/v1/wiki/timeline")
    async def get_timeline(session_id: str = DEFAULT_SESSION_ID) -> TimelineResponse:
        """Return the complete timeline for a wiki session."""
        try:
            content = await wiki_manager.read_timeline(session_id)
        except Exception as error:
            raise _handle_error(error) from error
        return TimelineResponse(session_id=session_id, content=content)

    @app.get("/api/v1/wiki/files")
    async def get_files(session_id: str = DEFAULT_SESSION_ID) -> WikiFilesResponse:
        """Return metadata for every file in a wiki session."""
        try:
            files = await wiki_manager.list_files(session_id)
        except Exception as error:
            raise _handle_error(error) from error
        return WikiFilesResponse(session_id=session_id, files=files)

    @app.get("/api/v1/wiki/actors/{actor_id}/files")
    async def get_actor_files(
        actor_id: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> ActorFilesResponse:
        """Return actor-specific files for runtime context injection."""
        try:
            files, contents = await wiki_manager.get_actor_files(actor_id, session_id)
        except Exception as error:
            raise _handle_error(error) from error
        return ActorFilesResponse(
            session_id=session_id,
            actor_id=actor_id,
            files=files,
            contents=contents,
        )

    @app.get("/api/v1/wiki/export")
    async def export_wiki(session_id: str = DEFAULT_SESSION_ID) -> Response:
        """Return a zip archive of one wiki session."""
        try:
            content = await wiki_manager.export_session(session_id)
        except Exception as error:
            raise _handle_error(error) from error
        headers = {"Content-Disposition": f'attachment; filename="{session_id}-wiki.zip"'}
        return Response(content=content, media_type="application/zip", headers=headers)

    app.mount("/mcp", mcp_app)
    return app


@mcp.tool
async def read_state_file(path: str, session_id: str = DEFAULT_SESSION_ID) -> str:
    """Read a complete state file from the Wiki.

    Args:
        path: State filename or `States/`-relative Markdown path.
        session_id: Target wiki session identifier.

    Returns:
        Complete Markdown content for the requested state file.
    """
    return await manager.read_state_file(path, session_id)


@mcp.tool
async def edit_state_file(
    path: str,
    content: str,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:
    """Create or replace a state file in the Wiki.

    Args:
        path: State filename or `States/`-relative Markdown path.
        content: Complete Markdown content to write.
        session_id: Target wiki session identifier.

    Returns:
        The written Markdown content.
    """
    return await manager.edit_state_file(path, content, session_id)


@mcp.tool
async def read_timeline(session_id: str = DEFAULT_SESSION_ID) -> str:
    """Read the complete simulation timeline.

    Args:
        session_id: Target wiki session identifier.

    Returns:
        Complete Markdown content for `Timeline.md`.
    """
    return await manager.read_timeline(session_id)


@mcp.tool
async def append_to_timeline(
    entry: str,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:
    """Append one official event to the simulation timeline.

    Args:
        entry: Markdown event entry to append.
        session_id: Target wiki session identifier.

    Returns:
        Updated timeline content.
    """
    return await manager.append_to_timeline(entry, session_id)


@mcp.tool
async def read_actor_file(actor_id: str, session_id: str = DEFAULT_SESSION_ID) -> str:
    """Read a complete actor file from the Wiki.

    Args:
        actor_id: Actor identifier or Markdown filename.
        session_id: Target wiki session identifier.

    Returns:
        Complete Markdown content for the requested actor file.
    """
    return await manager.read_actor_file(actor_id, session_id)


@mcp.tool
async def edit_actor_file(
    actor_id: str,
    content: str,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:
    """Create or replace an actor file in the Wiki.

    Args:
        actor_id: Actor identifier or Markdown filename.
        content: Complete Markdown content to write.
        session_id: Target wiki session identifier.

    Returns:
        The written Markdown content.
    """
    return await manager.edit_actor_file(actor_id, content, session_id)


@mcp.tool
async def append_to_actor_memory(
    actor_id: str,
    entry: str,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:
    """Append one private memory entry to an actor file.

    Args:
        actor_id: Actor identifier or Markdown filename.
        entry: Markdown memory entry to append.
        session_id: Target wiki session identifier.

    Returns:
        Updated actor Markdown content.
    """
    return await manager.append_to_actor_memory(actor_id, entry, session_id)


@mcp.tool
async def delete_file(path: str, session_id: str = DEFAULT_SESSION_ID) -> str:
    """Delete one state or actor file from the Wiki.

    Args:
        path: Wiki-relative Markdown path to delete.
        session_id: Target wiki session identifier.

    Returns:
        A confirmation message.
    """
    await manager.delete_file(path, session_id)
    return f"Deleted {path}"


app = create_app(manager)


if __name__ == "__main__":
    logger.info(
        "Initializing Wiki Service",
        extra={
            "host": "0.0.0.0",
            "port": config.service.port,
            "mcp_transport": "streamable_http",
        },
    )
    uvicorn.run(app, host="0.0.0.0", port=config.service.port)
