"""Resolve MCP tools into role-scoped LangChain tool sets."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, cast

from langchain_core.tools import BaseTool, tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import (
    SSEConnection,
    StdioConnection,
    StreamableHttpConnection,
    WebsocketConnection,
)
from langgraph.prebuilt import InjectedState

from agent_service.schema import MCPServersSettings

type MCPConnection = (
    StdioConnection | SSEConnection | StreamableHttpConnection | WebsocketConnection
)


class AgentRole(StrEnum):
    """Identify agent roles that receive different tool capabilities."""

    WORLD_BUILDER = "world_builder"
    SIMULATION_ORCHESTRATOR = "simulation_orchestrator"
    ACTOR = "actor"
    REPORT_AGENT = "report_agent"


class ToolCapability(StrEnum):
    """Identify internal capabilities independent of MCP tool names."""

    NEWS_SEARCH_RECENT = "news.search_recent"
    NEWS_DEEP_RESEARCH = "news.deep_research"
    NEWS_EXTRACT_ARTICLE = "news.extract_article"
    WIKI_READ_STATE = "wiki.read_state"
    WIKI_EDIT_STATE = "wiki.edit_state"
    WIKI_READ_TIMELINE = "wiki.read_timeline"
    WIKI_APPEND_TIMELINE = "wiki.append_timeline"
    WIKI_READ_ACTOR = "wiki.read_actor"
    WIKI_EDIT_ACTOR = "wiki.edit_actor"
    WIKI_APPEND_ACTOR_MEMORY = "wiki.append_actor_memory"
    WIKI_DELETE_FILE = "wiki.delete_file"


@dataclass(frozen=True)
class CapabilityBinding:
    """Map one internal capability to one MCP tool."""

    capability: ToolCapability
    server_name: str
    tool_name: str
    exposed_name: str
    role_constraint: str
    inject_session_id: bool = False


TOOL_BINDINGS: dict[ToolCapability, CapabilityBinding] = {
    ToolCapability.NEWS_SEARCH_RECENT: CapabilityBinding(
        capability=ToolCapability.NEWS_SEARCH_RECENT,
        server_name="news_service",
        tool_name="search_recent_news",
        exposed_name="news_search_recent_news",
        role_constraint="Use before writing Wiki files to ground the scenario in current events.",
    ),
    ToolCapability.NEWS_DEEP_RESEARCH: CapabilityBinding(
        capability=ToolCapability.NEWS_DEEP_RESEARCH,
        server_name="news_service",
        tool_name="search_deep_research",
        exposed_name="news_search_deep_research",
        role_constraint="Use for background context, institutions, and durable constraints.",
    ),
    ToolCapability.NEWS_EXTRACT_ARTICLE: CapabilityBinding(
        capability=ToolCapability.NEWS_EXTRACT_ARTICLE,
        server_name="news_service",
        tool_name="extract_article_content",
        exposed_name="news_extract_article_content",
        role_constraint="Use only for URLs returned by research tools.",
    ),
    ToolCapability.WIKI_READ_STATE: CapabilityBinding(
        capability=ToolCapability.WIKI_READ_STATE,
        server_name="wiki_service",
        tool_name="read_state_file",
        exposed_name="wiki_read_state_file",
        role_constraint="Read existing state files before replacing them.",
        inject_session_id=True,
    ),
    ToolCapability.WIKI_EDIT_STATE: CapabilityBinding(
        capability=ToolCapability.WIKI_EDIT_STATE,
        server_name="wiki_service",
        tool_name="edit_state_file",
        exposed_name="wiki_edit_state_file",
        role_constraint=(
            "Write only complete Markdown state files with a title and short description."
        ),
        inject_session_id=True,
    ),
    ToolCapability.WIKI_READ_TIMELINE: CapabilityBinding(
        capability=ToolCapability.WIKI_READ_TIMELINE,
        server_name="wiki_service",
        tool_name="read_timeline",
        exposed_name="wiki_read_timeline",
        role_constraint="Read timeline context only; do not create official events.",
        inject_session_id=True,
    ),
    ToolCapability.WIKI_APPEND_TIMELINE: CapabilityBinding(
        capability=ToolCapability.WIKI_APPEND_TIMELINE,
        server_name="wiki_service",
        tool_name="append_to_timeline",
        exposed_name="wiki_append_to_timeline",
        role_constraint="Append only validated official simulation events.",
        inject_session_id=True,
    ),
    ToolCapability.WIKI_READ_ACTOR: CapabilityBinding(
        capability=ToolCapability.WIKI_READ_ACTOR,
        server_name="wiki_service",
        tool_name="read_actor_file",
        exposed_name="wiki_read_actor_file",
        role_constraint="Read actor files before replacing them.",
        inject_session_id=True,
    ),
    ToolCapability.WIKI_EDIT_ACTOR: CapabilityBinding(
        capability=ToolCapability.WIKI_EDIT_ACTOR,
        server_name="wiki_service",
        tool_name="edit_actor_file",
        exposed_name="wiki_edit_actor_file",
        role_constraint=(
            "Write only complete Markdown actor sheets with a title and short description."
        ),
        inject_session_id=True,
    ),
    ToolCapability.WIKI_APPEND_ACTOR_MEMORY: CapabilityBinding(
        capability=ToolCapability.WIKI_APPEND_ACTOR_MEMORY,
        server_name="wiki_service",
        tool_name="append_to_actor_memory",
        exposed_name="wiki_append_to_actor_memory",
        role_constraint="Append only private actor memory entries.",
        inject_session_id=True,
    ),
    ToolCapability.WIKI_DELETE_FILE: CapabilityBinding(
        capability=ToolCapability.WIKI_DELETE_FILE,
        server_name="wiki_service",
        tool_name="delete_file",
        exposed_name="wiki_delete_file",
        role_constraint="Delete only files that are explicitly obsolete.",
        inject_session_id=True,
    ),
}


ROLE_PROFILES: dict[AgentRole, tuple[ToolCapability, ...]] = {
    AgentRole.WORLD_BUILDER: (
        ToolCapability.NEWS_SEARCH_RECENT,
        ToolCapability.NEWS_DEEP_RESEARCH,
        ToolCapability.NEWS_EXTRACT_ARTICLE,
        ToolCapability.WIKI_READ_STATE,
        ToolCapability.WIKI_EDIT_STATE,
        ToolCapability.WIKI_READ_TIMELINE,
        ToolCapability.WIKI_READ_ACTOR,
        ToolCapability.WIKI_EDIT_ACTOR,
    ),
    AgentRole.SIMULATION_ORCHESTRATOR: (
        ToolCapability.WIKI_READ_STATE,
        ToolCapability.WIKI_EDIT_STATE,
        ToolCapability.WIKI_READ_TIMELINE,
        ToolCapability.WIKI_APPEND_TIMELINE,
        ToolCapability.WIKI_READ_ACTOR,
        ToolCapability.WIKI_EDIT_ACTOR,
        ToolCapability.WIKI_DELETE_FILE,
    ),
    AgentRole.ACTOR: (
        ToolCapability.WIKI_READ_STATE,
        ToolCapability.WIKI_READ_TIMELINE,
        ToolCapability.WIKI_APPEND_ACTOR_MEMORY,
    ),
    AgentRole.REPORT_AGENT: (
        ToolCapability.WIKI_READ_STATE,
        ToolCapability.WIKI_READ_TIMELINE,
        ToolCapability.WIKI_READ_ACTOR,
    ),
}


class ToolRegistry:
    """Index discovered MCP tools and resolve role-specific tool sets."""

    def __init__(self, discovered_tools: Mapping[str, list[BaseTool]]) -> None:
        """Initialize the registry from tools grouped by MCP server.

        Args:
            discovered_tools: LangChain tools keyed by MCP server name.
        """
        self._tools_by_key: dict[tuple[str, str], BaseTool] = {}
        for server_name, tools in discovered_tools.items():
            seen_names: set[str] = set()
            for discovered_tool in tools:
                if discovered_tool.name in seen_names:
                    msg = f"Duplicate MCP tool {server_name}.{discovered_tool.name}"
                    raise ValueError(msg)
                seen_names.add(discovered_tool.name)
                self._tools_by_key[(server_name, discovered_tool.name)] = discovered_tool

    @classmethod
    async def discover(cls, settings: MCPServersSettings) -> "ToolRegistry":
        """Discover tools from configured MCP services.

        Args:
            settings: Agent service MCP server configuration.

        Returns:
            A registry populated with tools from all configured MCP services.
        """
        client = MultiServerMCPClient(_build_mcp_connections(settings))
        discovered: dict[str, list[BaseTool]] = {}
        for server_name in ("wiki_service", "news_service"):
            discovered[server_name] = await client.get_tools(server_name=server_name)
        return cls(discovered)

    def resolve_for_role(self, role: AgentRole | str) -> list[BaseTool]:
        """Return wrapped tools allowed for one agent role.

        Args:
            role: Agent role enum value or string value.

        Returns:
            LangChain tools with stable model-facing names.

        Raises:
            ValueError: If the role is unknown or the resolved names are duplicated.
            LookupError: If a required capability maps to an undiscovered MCP tool.
        """
        agent_role = _coerce_role(role)
        capabilities = ROLE_PROFILES.get(agent_role)
        if capabilities is None:
            msg = f"Unknown agent role: {role}"
            raise ValueError(msg)

        resolved_tools: list[BaseTool] = []
        exposed_names: set[str] = set()
        for capability in capabilities:
            binding = TOOL_BINDINGS[capability]
            original_tool = self._tools_by_key.get((binding.server_name, binding.tool_name))
            if original_tool is None:
                msg = (
                    "Missing MCP tool for capability "
                    f"{binding.capability}: {binding.server_name}.{binding.tool_name}"
                )
                raise LookupError(msg)
            if binding.exposed_name in exposed_names:
                msg = f"Duplicate exposed tool name: {binding.exposed_name}"
                raise ValueError(msg)
            exposed_names.add(binding.exposed_name)
            resolved_tools.append(_wrap_tool(original_tool, binding))
        return resolved_tools


def _coerce_role(role: AgentRole | str) -> AgentRole:
    """Convert a role string into an `AgentRole`."""
    try:
        return role if isinstance(role, AgentRole) else AgentRole(role)
    except ValueError as error:
        msg = f"Unknown agent role: {role}"
        raise ValueError(msg) from error


def _build_mcp_connections(settings: MCPServersSettings) -> dict[str, MCPConnection]:
    """Build MultiServerMCPClient connection dictionaries."""
    connections: dict[str, MCPConnection] = {}
    for server_name in ("wiki_service", "news_service"):
        server = getattr(settings, server_name)
        connections[server_name] = cast(
            MCPConnection, {"transport": server.transport, "url": server.url}
        )
    return connections


def _wrap_tool(original_tool: BaseTool, binding: CapabilityBinding) -> BaseTool:
    """Return a stable, constrained model-facing wrapper for one MCP tool."""
    if binding.inject_session_id:
        return _wrap_wiki_tool(original_tool, binding)
    return original_tool.model_copy(
        update={
            "name": binding.exposed_name,
            "description": _describe_tool(original_tool, binding),
        }
    )


def _describe_tool(original_tool: BaseTool, binding: CapabilityBinding) -> str:
    """Return the original description plus registry-level constraints."""
    return f"{original_tool.description}\n\nConstraint: {binding.role_constraint}"


def _wrap_wiki_tool(original_tool: BaseTool, binding: CapabilityBinding) -> BaseTool:
    """Wrap Wiki tools so graph state supplies the session identifier."""
    description = _describe_tool(original_tool, binding)
    if binding.tool_name == "read_state_file":

        @tool(binding.exposed_name, description=description)
        async def read_state_file(
            path: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read a complete state file from the active Wiki session."""
            result = await original_tool.ainvoke({"path": path, "session_id": session_id})
            return str(result)

        return read_state_file
    if binding.tool_name == "edit_state_file":

        @tool(binding.exposed_name, description=description)
        async def edit_state_file(
            path: str,
            content: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Create or replace a state file in the active Wiki session."""
            result = await original_tool.ainvoke(
                {"path": path, "content": content, "session_id": session_id}
            )
            return str(result)

        return edit_state_file
    if binding.tool_name == "read_timeline":

        @tool(binding.exposed_name, description=description)
        async def read_timeline(
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read the complete timeline from the active Wiki session."""
            result = await original_tool.ainvoke({"session_id": session_id})
            return str(result)

        return read_timeline
    if binding.tool_name == "append_to_timeline":

        @tool(binding.exposed_name, description=description)
        async def append_to_timeline(
            entry: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Append one official event to the active Wiki session."""
            result = await original_tool.ainvoke({"entry": entry, "session_id": session_id})
            return str(result)

        return append_to_timeline
    if binding.tool_name == "read_actor_file":

        @tool(binding.exposed_name, description=description)
        async def read_actor_file(
            actor_id: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Read a complete actor file from the active Wiki session."""
            result = await original_tool.ainvoke({"actor_id": actor_id, "session_id": session_id})
            return str(result)

        return read_actor_file
    if binding.tool_name == "edit_actor_file":

        @tool(binding.exposed_name, description=description)
        async def edit_actor_file(
            actor_id: str,
            content: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Create or replace an actor file in the active Wiki session."""
            result = await original_tool.ainvoke(
                {"actor_id": actor_id, "content": content, "session_id": session_id}
            )
            return str(result)

        return edit_actor_file
    if binding.tool_name == "append_to_actor_memory":

        @tool(binding.exposed_name, description=description)
        async def append_to_actor_memory(
            actor_id: str,
            entry: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Append private actor memory to the active Wiki session."""
            result = await original_tool.ainvoke(
                {"actor_id": actor_id, "entry": entry, "session_id": session_id}
            )
            return str(result)

        return append_to_actor_memory
    if binding.tool_name == "delete_file":

        @tool(binding.exposed_name, description=description)
        async def delete_file(
            path: str,
            session_id: Annotated[str, InjectedState("session_id")],
        ) -> str:
            """Delete one file from the active Wiki session."""
            result = await original_tool.ainvoke({"path": path, "session_id": session_id})
            return str(result)

        return delete_file

    msg = f"Cannot inject session_id for unknown Wiki tool: {binding.tool_name}"
    raise ValueError(msg)
