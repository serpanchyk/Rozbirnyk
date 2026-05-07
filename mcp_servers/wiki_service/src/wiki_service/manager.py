"""Manage filesystem-backed wiki sessions for API routes and MCP tools.

Data Flow: API or MCP Request -> Path Validation -> Session Filesystem Operation
-> Structured Result.

Async Behavior: Public methods expose asynchronous call sites and delegate blocking
filesystem work to worker threads.
"""

import asyncio
import re
import shutil
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from wiki_service.models import WikiFileMetadata

DEFAULT_SESSION_ID = "default"
TIMELINE_FILE = "Timeline.md"
STATES_DIR = "States"
ACTORS_DIR = "Actors"
PRIVATE_MEMORY_HEADING = "## Private Memory"
SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class WikiManager:
    """Coordinate validated wiki file operations for one storage root."""

    def __init__(self, root_dir: str | Path) -> None:
        """Initialize the manager with an absolute storage root.

        Args:
            root_dir: Directory containing per-session wiki folders.
        """
        self.root_dir = Path(root_dir).expanduser().resolve()

    async def reset(self, session_id: str = DEFAULT_SESSION_ID) -> None:
        """Recreate a session wiki with empty state, actor, and timeline files.

        Args:
            session_id: Target wiki session identifier.
        """
        await asyncio.to_thread(self._reset_sync, session_id)

    async def read_timeline(self, session_id: str = DEFAULT_SESSION_ID) -> str:
        """Read the complete timeline for a session.

        Args:
            session_id: Target wiki session identifier.

        Returns:
            The complete timeline content.
        """
        return await asyncio.to_thread(self._read_timeline_sync, session_id)

    async def append_to_timeline(
        self,
        entry: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Append an official event entry to the timeline.

        Args:
            entry: Markdown entry to append.
            session_id: Target wiki session identifier.

        Returns:
            The updated timeline content.
        """
        return await asyncio.to_thread(self._append_to_timeline_sync, entry, session_id)

    async def read_state_file(
        self,
        path: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Read a complete state file.

        Args:
            path: State filename or `States/`-relative Markdown path.
            session_id: Target wiki session identifier.

        Returns:
            The complete state file content.
        """
        return await asyncio.to_thread(self._read_state_file_sync, path, session_id)

    async def edit_state_file(
        self,
        path: str,
        content: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Create or replace a complete state file.

        Args:
            path: State filename or `States/`-relative Markdown path.
            content: New Markdown content.
            session_id: Target wiki session identifier.

        Returns:
            The updated state file content.
        """
        return await asyncio.to_thread(self._edit_state_file_sync, path, content, session_id)

    async def read_actor_file(
        self,
        actor_id: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Read a complete actor file.

        Args:
            actor_id: Actor identifier or Markdown filename.
            session_id: Target wiki session identifier.

        Returns:
            The complete actor file content.
        """
        return await asyncio.to_thread(self._read_actor_file_sync, actor_id, session_id)

    async def edit_actor_file(
        self,
        actor_id: str,
        content: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Create or replace a complete actor file.

        Args:
            actor_id: Actor identifier or Markdown filename.
            content: New Markdown content.
            session_id: Target wiki session identifier.

        Returns:
            The updated actor file content.
        """
        return await asyncio.to_thread(self._edit_actor_file_sync, actor_id, content, session_id)

    async def append_to_actor_memory(
        self,
        actor_id: str,
        entry: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> str:
        """Append a private memory entry to an actor file.

        Args:
            actor_id: Actor identifier or Markdown filename.
            entry: Markdown memory entry to append.
            session_id: Target wiki session identifier.

        Returns:
            The updated actor file content.
        """
        return await asyncio.to_thread(
            self._append_to_actor_memory_sync,
            actor_id,
            entry,
            session_id,
        )

    async def delete_file(
        self,
        path: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> None:
        """Delete one state or actor file from a session.

        Args:
            path: Wiki-relative Markdown path to delete.
            session_id: Target wiki session identifier.

        Raises:
            ValueError: If the path targets `Timeline.md` or escapes the session.
        """
        await asyncio.to_thread(self._delete_file_sync, path, session_id)

    async def list_files(
        self,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> list[WikiFileMetadata]:
        """List title and short description metadata for all wiki files.

        Args:
            session_id: Target wiki session identifier.

        Returns:
            Metadata for timeline, state, and actor files.
        """
        return await asyncio.to_thread(self._list_files_sync, session_id)

    async def get_actor_files(
        self,
        actor_id: str,
        session_id: str = DEFAULT_SESSION_ID,
    ) -> tuple[list[WikiFileMetadata], dict[str, str]]:
        """Read actor-specific file metadata and content for context injection.

        Args:
            actor_id: Actor identifier or Markdown filename.
            session_id: Target wiki session identifier.

        Returns:
            A tuple of metadata and file contents keyed by wiki-relative path.
        """
        return await asyncio.to_thread(self._get_actor_files_sync, actor_id, session_id)

    async def export_session(self, session_id: str = DEFAULT_SESSION_ID) -> bytes:
        """Create a zip archive for one wiki session.

        Args:
            session_id: Target wiki session identifier.

        Returns:
            Zip archive bytes containing session files.
        """
        return await asyncio.to_thread(self._export_session_sync, session_id)

    def _reset_sync(self, session_id: str) -> None:
        session_dir = self._session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir)
        (session_dir / STATES_DIR).mkdir(parents=True, exist_ok=True)
        (session_dir / ACTORS_DIR).mkdir(parents=True, exist_ok=True)
        (session_dir / TIMELINE_FILE).write_text("# Timeline\n\n", encoding="utf-8")

    def _read_timeline_sync(self, session_id: str) -> str:
        timeline = self._timeline_path(session_id)
        self._ensure_session(session_id)
        return timeline.read_text(encoding="utf-8")

    def _append_to_timeline_sync(self, entry: str, session_id: str) -> str:
        self._ensure_session(session_id)
        timeline = self._timeline_path(session_id)
        normalized = self._normalize_append_entry(entry)
        with timeline.open("a", encoding="utf-8") as file:
            file.write(normalized)
        return timeline.read_text(encoding="utf-8")

    def _read_state_file_sync(self, path: str, session_id: str) -> str:
        self._ensure_session(session_id)
        state_path = self._state_path(path, session_id)
        return state_path.read_text(encoding="utf-8")

    def _edit_state_file_sync(self, path: str, content: str, session_id: str) -> str:
        self._ensure_session(session_id)
        state_path = self._state_path(path, session_id)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(content, encoding="utf-8")
        return content

    def _read_actor_file_sync(self, actor_id: str, session_id: str) -> str:
        self._ensure_session(session_id)
        actor_path = self._actor_path(actor_id, session_id)
        return actor_path.read_text(encoding="utf-8")

    def _edit_actor_file_sync(self, actor_id: str, content: str, session_id: str) -> str:
        self._ensure_session(session_id)
        actor_path = self._actor_path(actor_id, session_id)
        actor_path.parent.mkdir(parents=True, exist_ok=True)
        actor_path.write_text(content, encoding="utf-8")
        return content

    def _append_to_actor_memory_sync(
        self,
        actor_id: str,
        entry: str,
        session_id: str,
    ) -> str:
        self._ensure_session(session_id)
        actor_path = self._actor_path(actor_id, session_id)
        content = actor_path.read_text(encoding="utf-8")
        normalized = self._normalize_append_entry(entry)
        if PRIVATE_MEMORY_HEADING in content:
            content = content.rstrip() + normalized
        else:
            content = content.rstrip() + f"\n\n{PRIVATE_MEMORY_HEADING}\n" + normalized
        actor_path.write_text(content, encoding="utf-8")
        return content

    def _delete_file_sync(self, path: str, session_id: str) -> None:
        self._ensure_session(session_id)
        target = self._wiki_path(path, session_id)
        if target.name == TIMELINE_FILE:
            raise ValueError("Timeline.md cannot be deleted through MCP.")
        if target.is_dir():
            raise ValueError("Only files can be deleted.")
        target.unlink()

    def _list_files_sync(self, session_id: str) -> list[WikiFileMetadata]:
        self._ensure_session(session_id)
        session_dir = self._session_dir(session_id)
        paths = [self._timeline_path(session_id)]
        paths.extend(sorted((session_dir / STATES_DIR).rglob("*.md")))
        paths.extend(sorted((session_dir / ACTORS_DIR).rglob("*.md")))
        return [self._metadata_for_path(path, session_dir) for path in paths if path.exists()]

    def _get_actor_files_sync(
        self,
        actor_id: str,
        session_id: str,
    ) -> tuple[list[WikiFileMetadata], dict[str, str]]:
        self._ensure_session(session_id)
        session_dir = self._session_dir(session_id)
        actor_path = self._actor_path(actor_id, session_id)
        content = actor_path.read_text(encoding="utf-8")
        metadata = self._metadata_for_path(actor_path, session_dir)
        return [metadata], {metadata.path: content}

    def _export_session_sync(self, session_id: str) -> bytes:
        self._ensure_session(session_id)
        session_dir = self._session_dir(session_id)
        archive = BytesIO()
        with ZipFile(archive, mode="w", compression=ZIP_DEFLATED) as zip_file:
            for path in sorted(session_dir.rglob("*")):
                if path.is_file():
                    zip_file.write(path, path.relative_to(session_dir).as_posix())
        return archive.getvalue()

    def _ensure_session(self, session_id: str) -> None:
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            self._reset_sync(session_id)

    def _session_dir(self, session_id: str) -> Path:
        if not SESSION_PATTERN.fullmatch(session_id):
            raise ValueError(
                "Session ID may only contain letters, numbers, dots, dashes, and underscores."
            )
        return self.root_dir / session_id

    def _timeline_path(self, session_id: str) -> Path:
        return self._session_dir(session_id) / TIMELINE_FILE

    def _state_path(self, path: str, session_id: str) -> Path:
        raw_path = Path(path)
        if raw_path.parts and raw_path.parts[0] == STATES_DIR:
            wiki_path = raw_path
        else:
            wiki_path = Path(STATES_DIR) / raw_path
        return self._wiki_path(wiki_path.as_posix(), session_id, required_root=STATES_DIR)

    def _actor_path(self, actor_id: str, session_id: str) -> Path:
        actor_name = actor_id if actor_id.endswith(".md") else f"{actor_id}.md"
        return self._wiki_path(f"{ACTORS_DIR}/{actor_name}", session_id, required_root=ACTORS_DIR)

    def _wiki_path(
        self,
        path: str,
        session_id: str,
        required_root: str | None = None,
    ) -> Path:
        raw_path = Path(path)
        if raw_path.is_absolute():
            raise ValueError("Wiki paths must be relative.")
        if raw_path.suffix != ".md":
            raise ValueError("Wiki files must use the .md extension.")
        if ".." in raw_path.parts:
            raise ValueError("Wiki paths cannot contain parent directory segments.")
        if required_root is not None and (not raw_path.parts or raw_path.parts[0] != required_root):
            raise ValueError(f"Wiki path must be under {required_root}/.")
        session_dir = self._session_dir(session_id).resolve()
        target = (session_dir / raw_path).resolve()
        if session_dir != target and session_dir not in target.parents:
            raise ValueError("Wiki path escapes the session directory.")
        return target

    def _metadata_for_path(self, path: Path, session_dir: Path) -> WikiFileMetadata:
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(session_dir).as_posix()
        return WikiFileMetadata(
            path=relative_path,
            title=self._extract_title(content, path),
            short_description=self._extract_short_description(content),
            kind=self._kind_for_path(relative_path),
        )

    def _extract_title(self, content: str, path: Path) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                title = line.removeprefix("# ").strip()
                if title:
                    return title
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _extract_short_description(self, content: str) -> str:
        for line in content.splitlines():
            if line.lower().startswith("short description:"):
                description = line.split(":", maxsplit=1)[1].strip()
                if description:
                    return description
        return "No short description provided."

    def _kind_for_path(self, path: str) -> str:
        if path == TIMELINE_FILE:
            return "timeline"
        if path.startswith(f"{STATES_DIR}/"):
            return "state"
        if path.startswith(f"{ACTORS_DIR}/"):
            return "actor"
        return "unknown"

    def _normalize_append_entry(self, entry: str) -> str:
        stripped = entry.strip()
        if not stripped:
            raise ValueError("Appended entry cannot be empty.")
        return f"\n{stripped}\n"
