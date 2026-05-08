"""Map internal tool capabilities to discovered MCP tools."""

from dataclasses import dataclass

from agent_service.tools.roles import ToolCapability


@dataclass(frozen=True)
class CapabilityBinding:
    """Map one internal capability to one MCP tool."""

    capability: ToolCapability
    server_name: str
    tool_name: str
    exposed_name: str
    role_constraint: str
    inject_session_id: bool = False

    @property
    def lookup_key(self) -> tuple[str, str]:
        """Return the discovered-tool lookup key for this binding."""
        return (self.server_name, self.tool_name)


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
