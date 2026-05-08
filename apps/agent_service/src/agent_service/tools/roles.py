"""Define agent roles and their allowed tool capabilities."""

from enum import StrEnum


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


def coerce_role(role: AgentRole | str) -> AgentRole:
    """Convert a role string into an `AgentRole`.

    Args:
        role: Agent role enum value or string value.

    Returns:
        Normalized agent role.

    Raises:
        ValueError: If the role is unknown.
    """
    try:
        return role if isinstance(role, AgentRole) else AgentRole(role)
    except ValueError as error:
        msg = f"Unknown agent role: {role}"
        raise ValueError(msg) from error
