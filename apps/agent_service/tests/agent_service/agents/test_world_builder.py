"""Unit tests for the World Builder LangGraph workflow."""

from collections.abc import Sequence
from typing import Any

import pytest
from agent_service.agents.base import AgentBase
from agent_service.agents.world_builder import (
    WorldBuilder,
    build_world_builder_initial_state,
    create_world_builder_graph,
)
from agent_service.tools.registry import ToolRegistry
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool, tool


class FakeBoundModel:
    """Return prepared model messages and record received prompts."""

    def __init__(self, responses: list[AIMessage]) -> None:
        """Initialize the fake model with deterministic responses."""
        self.responses = responses
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        """Return the next prepared response."""
        self.calls.append(list(messages))
        return self.responses.pop(0)


class FakeModel:
    """Expose bind_tools like a LangChain chat model."""

    def __init__(self, responses: list[AIMessage]) -> None:
        """Initialize the fake model."""
        self.bound_model = FakeBoundModel(responses)
        self.bound_tools: list[BaseTool] = []

    def bind_tools(self, tools: Sequence[BaseTool]) -> FakeBoundModel:
        """Record tools and return the bound fake model."""
        self.bound_tools = list(tools)
        return self.bound_model


def _make_registry() -> ToolRegistry:
    """Create a registry with the World Builder's required tools."""

    @tool("search_recent_news", description="Search recent news.")
    async def search_recent_news(query: str, days: int = 3) -> str:
        """Search recent news."""
        return f"recent:{query}:{days}"

    @tool("search_deep_research", description="Search deep research.")
    async def search_deep_research(query: str) -> str:
        """Search deep research."""
        return f"deep:{query}"

    @tool("extract_article_content", description="Extract articles.")
    async def extract_article_content(urls: list[str]) -> str:
        """Extract articles."""
        return ",".join(urls)

    @tool("read_state_file", description="Read state.")
    async def read_state_file(path: str, session_id: str) -> str:
        """Read state."""
        return f"state:{path}:{session_id}"

    @tool("edit_state_file", description="Edit state.")
    async def edit_state_file(path: str, content: str, session_id: str) -> str:
        """Edit state."""
        return f"edited-state:{path}:{content}:{session_id}"

    @tool("read_timeline", description="Read timeline.")
    async def read_timeline(session_id: str) -> str:
        """Read timeline."""
        return f"timeline:{session_id}"

    @tool("read_actor_file", description="Read actor.")
    async def read_actor_file(actor_id: str, session_id: str) -> str:
        """Read actor."""
        return f"actor:{actor_id}:{session_id}"

    @tool("edit_actor_file", description="Edit actor.")
    async def edit_actor_file(actor_id: str, content: str, session_id: str) -> str:
        """Edit actor."""
        return f"edited-actor:{actor_id}:{content}:{session_id}"

    return ToolRegistry(
        {
            "news_service": [
                search_recent_news,
                search_deep_research,
                extract_article_content,
            ],
            "wiki_service": [
                read_state_file,
                edit_state_file,
                read_timeline,
                read_actor_file,
                edit_actor_file,
            ],
        }
    )


@pytest.mark.asyncio
async def test_world_builder_graph_executes_tool_loop_and_terminates() -> None:
    """Verify the graph compiles, executes ToolNode, and stops without tool calls."""
    model = FakeModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "news_search_recent_news",
                        "args": {"query": "EU AI", "days": 2},
                        "id": "call-1",
                    }
                ],
            ),
            AIMessage(content="Created States/eu.md and Actors/parliament.md"),
        ]
    )
    graph = create_world_builder_graph(model, _make_registry())

    result: dict[str, Any] = await graph.ainvoke(
        build_world_builder_initial_state(
            scenario="the EU bans open-source AI models",
            session_id="scenario-1",
        )
    )

    assert {tool.name for tool in model.bound_tools} == {
        "news_search_recent_news",
        "news_search_deep_research",
        "news_extract_article_content",
        "wiki_read_state_file",
        "wiki_edit_state_file",
        "wiki_read_timeline",
        "wiki_read_actor_file",
        "wiki_edit_actor_file",
    }
    assert len(model.bound_model.calls) == 2
    assert result["messages"][-1].content == "Created States/eu.md and Actors/parliament.md"
    assert result["remaining_steps"] == 6


def test_world_builder_is_agent_base_subclass() -> None:
    """Verify the World Builder follows the shared agent class contract."""
    assert issubclass(WorldBuilder, AgentBase)


def test_world_builder_builds_initial_state_with_instance_defaults() -> None:
    """Verify the class owns World Builder initial state construction."""
    builder = WorldBuilder(FakeModel([AIMessage(content="done")]), _make_registry())

    state = builder.build_initial_state(
        scenario="Brazil joins OPEC",
        session_id="scenario-2",
    )

    assert state == {
        "messages": state["messages"],
        "scenario": "Brazil joins OPEC",
        "session_id": "scenario-2",
        "remaining_steps": 8,
    }
    assert state["messages"][0].content == "What if Brazil joins OPEC"


def test_world_builder_initial_state_includes_limits_when_provided() -> None:
    """Verify limit fields are propagated into the initial graph state."""
    state = build_world_builder_initial_state(
        scenario="Brazil joins OPEC",
        session_id="scenario-2",
        max_actors=3,
        max_state_files=5,
    )

    assert state["max_actors"] == 3
    assert state["max_state_files"] == 5


def test_world_builder_graph_rejects_models_without_tool_binding() -> None:
    """Verify graph construction fails if the model cannot bind tools."""
    with pytest.raises(TypeError, match="bind_tools"):
        create_world_builder_graph(object(), _make_registry())
