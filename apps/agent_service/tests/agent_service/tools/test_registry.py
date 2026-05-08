"""Unit tests for the agent service tool registry."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, TypedDict, cast

import pytest
from agent_service.tools.registry import AgentRole, ToolRegistry
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel


def _make_tool(name: str, handler: Callable[..., Awaitable[str]] | None = None) -> BaseTool:
    """Create a named async test tool."""
    if name == "search_recent_news":

        @tool(name, description="Search recent news.")
        async def search_recent_news(query: str, days: int = 3) -> str:
            """Search recent news."""
            return await _call_handler(handler, query=query, days=days)

        return search_recent_news
    if name == "search_deep_research":

        @tool(name, description="Search background research.")
        async def search_deep_research(query: str) -> str:
            """Search background research."""
            return await _call_handler(handler, query=query)

        return search_deep_research
    if name == "extract_article_content":

        @tool(name, description="Extract article content.")
        async def extract_article_content(urls: list[str]) -> str:
            """Extract article content."""
            return await _call_handler(handler, urls=urls)

        return extract_article_content
    if name == "read_state_file":

        @tool(name, description="Read state.")
        async def read_state_file(path: str, session_id: str) -> str:
            """Read state."""
            return await _call_handler(handler, path=path, session_id=session_id)

        return read_state_file
    if name == "edit_state_file":

        @tool(name, description="Edit state.")
        async def edit_state_file(path: str, content: str, session_id: str) -> str:
            """Edit state."""
            return await _call_handler(handler, path=path, content=content, session_id=session_id)

        return edit_state_file
    if name == "read_timeline":

        @tool(name, description="Read timeline.")
        async def read_timeline(session_id: str) -> str:
            """Read timeline."""
            return await _call_handler(handler, session_id=session_id)

        return read_timeline
    if name == "append_to_timeline":

        @tool(name, description="Append timeline.")
        async def append_to_timeline(entry: str, session_id: str) -> str:
            """Append timeline."""
            return await _call_handler(handler, entry=entry, session_id=session_id)

        return append_to_timeline
    if name == "read_actor_file":

        @tool(name, description="Read actor.")
        async def read_actor_file(actor_id: str, session_id: str) -> str:
            """Read actor."""
            return await _call_handler(handler, actor_id=actor_id, session_id=session_id)

        return read_actor_file
    if name == "edit_actor_file":

        @tool(name, description="Edit actor.")
        async def edit_actor_file(actor_id: str, content: str, session_id: str) -> str:
            """Edit actor."""
            return await _call_handler(
                handler, actor_id=actor_id, content=content, session_id=session_id
            )

        return edit_actor_file
    if name == "append_to_actor_memory":

        @tool(name, description="Append actor memory.")
        async def append_to_actor_memory(actor_id: str, entry: str, session_id: str) -> str:
            """Append actor memory."""
            return await _call_handler(
                handler, actor_id=actor_id, entry=entry, session_id=session_id
            )

        return append_to_actor_memory

    @tool(name, description="Delete file.")
    async def delete_file(path: str, session_id: str) -> str:
        """Delete file."""
        return await _call_handler(handler, path=path, session_id=session_id)

    return delete_file


async def _call_handler(handler: Callable[..., Awaitable[str]] | None, **kwargs: Any) -> str:
    """Call a test handler or return the received arguments."""
    if handler is None:
        return str(kwargs)
    return await handler(**kwargs)


def _make_registry() -> ToolRegistry:
    """Create a registry containing all News and Wiki MCP test tools."""
    return ToolRegistry(
        {
            "news_service": [
                _make_tool("search_recent_news"),
                _make_tool("search_deep_research"),
                _make_tool("extract_article_content"),
            ],
            "wiki_service": [
                _make_tool("read_state_file"),
                _make_tool("edit_state_file"),
                _make_tool("read_timeline"),
                _make_tool("append_to_timeline"),
                _make_tool("read_actor_file"),
                _make_tool("edit_actor_file"),
                _make_tool("append_to_actor_memory"),
                _make_tool("delete_file"),
            ],
        }
    )


def test_resolves_world_builder_tools_from_news_and_wiki_services() -> None:
    """Verify World Builder receives only its role profile tools."""
    tools = _make_registry().resolve_for_role(AgentRole.WORLD_BUILDER)
    names = {tool.name for tool in tools}

    assert "news_search_recent_news" in names
    assert "news_search_deep_research" in names
    assert "news_extract_article_content" in names
    assert "wiki_read_state_file" in names
    assert "wiki_edit_state_file" in names
    assert "wiki_read_timeline" in names
    assert "wiki_read_actor_file" in names
    assert "wiki_edit_actor_file" in names
    assert "wiki_append_to_timeline" not in names
    assert "wiki_append_to_actor_memory" not in names
    assert "wiki_delete_file" not in names


def test_rejects_unknown_role() -> None:
    """Verify unconfigured roles fail loudly."""
    with pytest.raises(ValueError, match="Unknown agent role"):
        _make_registry().resolve_for_role("unknown")


def test_rejects_missing_required_capability() -> None:
    """Verify a missing MCP tool fails during role resolution."""
    registry = ToolRegistry({"news_service": [], "wiki_service": []})

    with pytest.raises(LookupError, match="Missing MCP tool"):
        registry.resolve_for_role(AgentRole.WORLD_BUILDER)


def test_model_facing_tool_names_are_unique() -> None:
    """Verify exposed tool names do not collide."""
    tools = _make_registry().resolve_for_role(AgentRole.WORLD_BUILDER)
    names = [tool.name for tool in tools]

    assert len(names) == len(set(names))


@pytest.mark.asyncio
async def test_wiki_session_id_is_injected_from_graph_state() -> None:
    """Verify wrapped Wiki tools receive session_id from LangGraph state."""

    class ToolState(TypedDict):
        """Carry messages and session context through the test graph."""

        messages: Annotated[list[BaseMessage], add_messages]
        session_id: str

    received: dict[str, str] = {}

    async def record_call(**kwargs: str) -> str:
        received.update(kwargs)
        return "state content"

    registry = ToolRegistry(
        {
            "news_service": [
                _make_tool("search_recent_news"),
                _make_tool("search_deep_research"),
                _make_tool("extract_article_content"),
            ],
            "wiki_service": [
                _make_tool("read_state_file", record_call),
                _make_tool("edit_state_file"),
                _make_tool("read_timeline"),
                _make_tool("append_to_timeline"),
                _make_tool("read_actor_file"),
                _make_tool("edit_actor_file"),
                _make_tool("append_to_actor_memory"),
                _make_tool("delete_file"),
            ],
        }
    )
    read_tool = next(
        tool
        for tool in registry.resolve_for_role(AgentRole.WORLD_BUILDER)
        if tool.name == "wiki_read_state_file"
    )

    tool_call_schema = cast(type[BaseModel], read_tool.tool_call_schema)
    schema = tool_call_schema.model_json_schema()
    assert "session_id" not in schema["properties"]

    graph = StateGraph(ToolState)
    graph.add_node("tools", ToolNode([read_tool]))
    graph.add_edge(START, "tools")
    graph.add_edge("tools", END)
    compiled = cast(Any, graph.compile())

    initial_state: ToolState = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "wiki_read_state_file",
                        "args": {"path": "economy.md"},
                        "id": "call-1",
                    }
                ],
            )
        ],
        "session_id": "session-123",
    }
    result = await compiled.ainvoke(initial_state)

    assert received == {"path": "economy.md", "session_id": "session-123"}
    assert result["messages"][-1].content == "state content"
