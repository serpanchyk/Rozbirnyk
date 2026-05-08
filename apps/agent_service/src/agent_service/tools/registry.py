"""Resolve MCP tools into role-scoped LangChain tool sets."""

from collections.abc import Mapping

from langchain_core.tools import BaseTool

from agent_service.schema import MCPServersSettings
from agent_service.tools.bindings import TOOL_BINDINGS, CapabilityBinding
from agent_service.tools.discovery import MCPToolDiscovery
from agent_service.tools.roles import (
    ROLE_PROFILES,
    AgentRole,
    ToolCapability,
    coerce_role,
)
from agent_service.tools.wrappers import wrap_tool


class DiscoveredToolIndex:
    """Index discovered MCP tools by server and tool name."""

    def __init__(self, discovered_tools: Mapping[str, list[BaseTool]]) -> None:
        """Initialize an index from tools grouped by MCP server.

        Args:
            discovered_tools: LangChain tools keyed by MCP server name.
        """
        self._tools_by_key: dict[tuple[str, str], BaseTool] = {}
        for server_name, tools in discovered_tools.items():
            self._index_server_tools(server_name, tools)

    def get(self, binding: CapabilityBinding) -> BaseTool:
        """Return the discovered tool required by a capability binding.

        Args:
            binding: Binding that identifies the MCP server and tool.

        Returns:
            Discovered LangChain tool.

        Raises:
            LookupError: If the required tool was not discovered.
        """
        original_tool = self._tools_by_key.get(binding.lookup_key)
        if original_tool is None:
            msg = (
                "Missing MCP tool for capability "
                f"{binding.capability}: {binding.server_name}.{binding.tool_name}"
            )
            raise LookupError(msg)
        return original_tool

    def _index_server_tools(self, server_name: str, tools: list[BaseTool]) -> None:
        """Index tools for one MCP server and reject duplicate names."""
        seen_names: set[str] = set()
        for discovered_tool in tools:
            if discovered_tool.name in seen_names:
                msg = f"Duplicate MCP tool {server_name}.{discovered_tool.name}"
                raise ValueError(msg)
            seen_names.add(discovered_tool.name)
            self._tools_by_key[(server_name, discovered_tool.name)] = discovered_tool


class RoleToolResolver:
    """Resolve configured capabilities into wrapped role tools."""

    def __init__(self, tool_index: DiscoveredToolIndex) -> None:
        """Initialize the resolver with discovered tools.

        Args:
            tool_index: Index used to retrieve discovered MCP tools.
        """
        self._tool_index = tool_index

    def resolve(self, role: AgentRole | str) -> list[BaseTool]:
        """Return wrapped tools allowed for one agent role.

        Args:
            role: Agent role enum value or string value.

        Returns:
            LangChain tools with stable model-facing names.

        Raises:
            ValueError: If the role is unknown or resolved names are duplicated.
            LookupError: If a required capability maps to an undiscovered MCP tool.
        """
        agent_role = coerce_role(role)
        capabilities = ROLE_PROFILES.get(agent_role)
        if capabilities is None:
            msg = f"Unknown agent role: {role}"
            raise ValueError(msg)

        resolved_tools: list[BaseTool] = []
        exposed_names: set[str] = set()
        for capability in capabilities:
            binding = TOOL_BINDINGS[capability]
            self._ensure_unique_exposed_name(binding, exposed_names)
            original_tool = self._tool_index.get(binding)
            resolved_tools.append(wrap_tool(original_tool, binding))
        return resolved_tools

    def _ensure_unique_exposed_name(
        self,
        binding: CapabilityBinding,
        exposed_names: set[str],
    ) -> None:
        """Record a model-facing name and fail on collisions."""
        if binding.exposed_name in exposed_names:
            msg = f"Duplicate exposed tool name: {binding.exposed_name}"
            raise ValueError(msg)
        exposed_names.add(binding.exposed_name)


class ToolRegistry:
    """Index discovered MCP tools and resolve role-specific tool sets."""

    def __init__(self, discovered_tools: Mapping[str, list[BaseTool]]) -> None:
        """Initialize the registry from tools grouped by MCP server.

        Args:
            discovered_tools: LangChain tools keyed by MCP server name.
        """
        self._resolver = RoleToolResolver(DiscoveredToolIndex(discovered_tools))

    @classmethod
    async def discover(cls, settings: MCPServersSettings) -> "ToolRegistry":
        """Discover tools from configured MCP services.

        Args:
            settings: Agent service MCP server configuration.

        Returns:
            A registry populated with tools from all configured MCP services.
        """
        discovered = await MCPToolDiscovery(settings).discover()
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
        return self._resolver.resolve(role)


__all__ = [
    "ROLE_PROFILES",
    "TOOL_BINDINGS",
    "AgentRole",
    "CapabilityBinding",
    "DiscoveredToolIndex",
    "RoleToolResolver",
    "ToolCapability",
    "ToolRegistry",
]
