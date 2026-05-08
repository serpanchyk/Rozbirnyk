"""Wrap discovered MCP tools for role-safe agent use."""

from abc import ABC, abstractmethod
from typing import Annotated

from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import InjectedState

from agent_service.tools.bindings import CapabilityBinding


class BoundToolWrapper(ABC):
    """Create a model-facing tool from a discovered MCP tool and binding."""

    def __init__(self, original_tool: BaseTool, binding: CapabilityBinding) -> None:
        """Initialize a wrapper from discovered tool metadata.

        Args:
            original_tool: Tool returned by MCP discovery.
            binding: Registry binding that constrains the tool for a role.
        """
        self._original_tool = original_tool
        self._binding = binding

    @abstractmethod
    def wrap(self) -> BaseTool:
        """Return the wrapped LangChain tool."""

    @property
    def description(self) -> str:
        """Return the original description plus registry-level constraints."""
        return f"{self._original_tool.description}\n\nConstraint: {self._binding.role_constraint}"


class PassthroughToolWrapper(BoundToolWrapper):
    """Expose a discovered tool with registry-controlled name and description."""

    def wrap(self) -> BaseTool:
        """Return a renamed copy of the discovered tool."""
        return self._original_tool.model_copy(
            update={
                "name": self._binding.exposed_name,
                "description": self.description,
            }
        )


class SessionInjectedToolWrapper(BoundToolWrapper):
    """Base class for Wiki wrappers that inject session_id from graph state."""

    async def _call_original(self, args: dict[str, object]) -> str:
        """Invoke the original MCP tool and normalize its result."""
        result = await self._original_tool.ainvoke(args)
        return str(result)


class ReadStateFileWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki read-state tool."""

    def wrap(self) -> BaseTool:
        """Return a read-state tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def read_state_file(
            path: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read a complete state file from the active Wiki session."""
            return await self._call_original({"path": path, "session_id": session_id})

        return read_state_file


class EditStateFileWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki edit-state tool."""

    def wrap(self) -> BaseTool:
        """Return an edit-state tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def edit_state_file(
            path: str,
            content: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Create or replace a state file in the active Wiki session."""
            return await self._call_original(
                {"path": path, "content": content, "session_id": session_id}
            )

        return edit_state_file


class ReadTimelineWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki read-timeline tool."""

    def wrap(self) -> BaseTool:
        """Return a read-timeline tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def read_timeline(
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read the complete timeline from the active Wiki session."""
            return await self._call_original({"session_id": session_id})

        return read_timeline


class AppendTimelineWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki append-timeline tool."""

    def wrap(self) -> BaseTool:
        """Return an append-timeline tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def append_to_timeline(
            entry: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Append one official event to the active Wiki session."""
            return await self._call_original({"entry": entry, "session_id": session_id})

        return append_to_timeline


class ReadActorFileWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki read-actor tool."""

    def wrap(self) -> BaseTool:
        """Return a read-actor tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def read_actor_file(
            actor_id: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read a complete actor file from the active Wiki session."""
            return await self._call_original({"actor_id": actor_id, "session_id": session_id})

        return read_actor_file


class EditActorFileWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki edit-actor tool."""

    def wrap(self) -> BaseTool:
        """Return an edit-actor tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def edit_actor_file(
            actor_id: str,
            content: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Create or replace an actor file in the active Wiki session."""
            return await self._call_original(
                {"actor_id": actor_id, "content": content, "session_id": session_id}
            )

        return edit_actor_file


class AppendActorMemoryWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki append-actor-memory tool."""

    def wrap(self) -> BaseTool:
        """Return an append-actor-memory tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def append_to_actor_memory(
            actor_id: str,
            entry: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Append private actor memory to the active Wiki session."""
            return await self._call_original(
                {"actor_id": actor_id, "entry": entry, "session_id": session_id}
            )

        return append_to_actor_memory


class DeleteFileWrapper(SessionInjectedToolWrapper):
    """Wrap the Wiki delete-file tool."""

    def wrap(self) -> BaseTool:
        """Return a delete-file tool with injected session_id."""

        @tool(self._binding.exposed_name, description=self.description)
        async def delete_file(
            path: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Delete one file from the active Wiki session."""
            return await self._call_original({"path": path, "session_id": session_id})

        return delete_file


SESSION_INJECTED_WRAPPERS: dict[str, type[SessionInjectedToolWrapper]] = {
    "read_state_file": ReadStateFileWrapper,
    "edit_state_file": EditStateFileWrapper,
    "read_timeline": ReadTimelineWrapper,
    "append_to_timeline": AppendTimelineWrapper,
    "read_actor_file": ReadActorFileWrapper,
    "edit_actor_file": EditActorFileWrapper,
    "append_to_actor_memory": AppendActorMemoryWrapper,
    "delete_file": DeleteFileWrapper,
}


def wrap_tool(original_tool: BaseTool, binding: CapabilityBinding) -> BaseTool:
    """Return a stable, constrained model-facing wrapper for one MCP tool."""
    if not binding.inject_session_id:
        return PassthroughToolWrapper(original_tool, binding).wrap()
    wrapper_cls = SESSION_INJECTED_WRAPPERS.get(binding.tool_name)
    if wrapper_cls is None:
        msg = f"Cannot inject session_id for unknown Wiki tool: {binding.tool_name}"
        raise ValueError(msg)
    return wrapper_cls(original_tool, binding).wrap()
