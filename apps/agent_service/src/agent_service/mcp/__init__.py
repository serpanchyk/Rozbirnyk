"""Public interface for the MCP integration layer."""

from agent_service.mcp.manager import MCPResourceManager, filter_wiki_tools_for_role

__all__ = ["MCPResourceManager", "filter_wiki_tools_for_role"]
