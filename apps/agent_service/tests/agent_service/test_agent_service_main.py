"""Test World Builder run lifecycle and API routes."""

import asyncio
from collections.abc import Sequence

import pytest
from agent_service.main import create_app
from agent_service.models import (
    WikiFileSummary,
    WorldBuilderEventType,
    WorldBuilderLimits,
    WorldBuilderRunRequest,
    WorldBuilderStatus,
)
from agent_service.run_manager import WorldBuilderRunManager
from agent_service.tools.registry import ToolRegistry
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool, tool


class FakeBoundModel:
    """Return prepared model messages and record received prompts."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = responses
        self.calls: list[list[BaseMessage]] = []

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        return self.responses.pop(0)


class FakeModel:
    """Expose bind_tools like a LangChain chat model."""

    def __init__(self, responses: list[AIMessage]) -> None:
        self.bound_model = FakeBoundModel(responses)
        self.bound_tools: list[BaseTool] = []

    def bind_tools(self, tools: Sequence[BaseTool]) -> FakeBoundModel:
        self.bound_tools = list(tools)
        return self.bound_model


def _make_registry() -> ToolRegistry:
    @tool("search_recent_news", description="Search recent news.")
    async def search_recent_news(query: str, days: int = 3) -> str:
        return f"recent:{query}:{days}"

    @tool("search_deep_research", description="Search deep research.")
    async def search_deep_research(query: str) -> str:
        return f"deep:{query}"

    @tool("extract_article_content", description="Extract articles.")
    async def extract_article_content(urls: list[str]) -> str:
        return ",".join(urls)

    @tool("read_state_file", description="Read state.")
    async def read_state_file(path: str, session_id: str) -> str:
        return f"state:{path}:{session_id}"

    @tool("edit_state_file", description="Edit state.")
    async def edit_state_file(path: str, content: str, session_id: str) -> str:
        return f"edited-state:{path}:{content}:{session_id}"

    @tool("read_timeline", description="Read timeline.")
    async def read_timeline(session_id: str) -> str:
        return f"timeline:{session_id}"

    @tool("read_actor_file", description="Read actor.")
    async def read_actor_file(actor_id: str, session_id: str) -> str:
        return f"actor:{actor_id}:{session_id}"

    @tool("edit_actor_file", description="Edit actor.")
    async def edit_actor_file(actor_id: str, content: str, session_id: str) -> str:
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


async def _wait_for_terminal_status(manager: WorldBuilderRunManager, run_id: str) -> str:
    for _ in range(100):
        status = manager.get_status(run_id)
        if status.status in {WorldBuilderStatus.COMPLETED, WorldBuilderStatus.FAILED}:
            return status.status
        await asyncio.sleep(0)
    raise AssertionError("Run did not finish in time.")


@pytest.mark.asyncio
async def test_run_manager_completes_and_summarizes_wiki_files() -> None:
    async def fetch_wiki_files(session_id: str) -> list[WikiFileSummary]:
        assert session_id == "scenario-1"
        return [
            WikiFileSummary(
                path="States/economy.md",
                title="Economy",
                short_description="Baseline.",
                kind="state",
            ),
            WikiFileSummary(
                path="Actors/parliament.md",
                title="Parliament",
                short_description="Decision maker.",
                kind="actor",
            ),
        ]

    manager = WorldBuilderRunManager(
        model=FakeModel([AIMessage(content="Created initial world.")]),
        tool_registry=_make_registry(),
        max_steps=8,
        hard_limits=WorldBuilderLimits(max_actors=4, max_state_files=4),
        fetch_wiki_files=fetch_wiki_files,
    )

    response = await manager.start_run(
        WorldBuilderRunRequest(
            session_id="scenario-1",
            scenario="Brazil joins OPEC",
            max_actors=10,
            max_state_files=2,
        )
    )
    terminal_status = await _wait_for_terminal_status(manager, response.run_id)
    final_status = manager.get_status(response.run_id)

    assert terminal_status == WorldBuilderStatus.COMPLETED
    assert final_status.effective_limits.max_actors == 4
    assert final_status.effective_limits.max_state_files == 2
    assert final_status.result_summary is not None
    assert len(final_status.result_summary.state_files) == 1
    assert len(final_status.result_summary.actor_files) == 1
    events = manager.list_events_for_session("scenario-1")
    assert events is not None
    assert [event.event for event in events.events] == [
        WorldBuilderEventType.STARTED,
        WorldBuilderEventType.RESEARCHING,
        WorldBuilderEventType.FILE_CREATED,
        WorldBuilderEventType.FILE_CREATED,
        WorldBuilderEventType.COMPLETED,
    ]


@pytest.mark.asyncio
async def test_run_manager_rejects_duplicate_active_session_runs() -> None:
    async def fetch_wiki_files(_: str) -> list[WikiFileSummary]:
        await asyncio.sleep(0.05)
        return []

    manager = WorldBuilderRunManager(
        model=FakeModel([AIMessage(content="done")]),
        tool_registry=_make_registry(),
        max_steps=8,
        hard_limits=WorldBuilderLimits(max_actors=4, max_state_files=4),
        fetch_wiki_files=fetch_wiki_files,
    )

    await manager.start_run(
        WorldBuilderRunRequest(session_id="scenario-1", scenario="Brazil joins OPEC")
    )

    with pytest.raises(ValueError, match="already has an active World Builder run"):
        await manager.start_run(
            WorldBuilderRunRequest(session_id="scenario-1", scenario="Brazil joins OPEC")
        )


@pytest.mark.asyncio
async def test_run_manager_fails_when_actor_limit_is_exceeded() -> None:
    async def fetch_wiki_files(_: str) -> list[WikiFileSummary]:
        return [
            WikiFileSummary(
                path="Actors/one.md",
                title="One",
                short_description="A.",
                kind="actor",
            ),
            WikiFileSummary(
                path="Actors/two.md",
                title="Two",
                short_description="B.",
                kind="actor",
            ),
        ]

    manager = WorldBuilderRunManager(
        model=FakeModel([AIMessage(content="done")]),
        tool_registry=_make_registry(),
        max_steps=8,
        hard_limits=WorldBuilderLimits(max_actors=1, max_state_files=4),
        fetch_wiki_files=fetch_wiki_files,
    )

    response = await manager.start_run(
        WorldBuilderRunRequest(session_id="scenario-1", scenario="Brazil joins OPEC")
    )
    terminal_status = await _wait_for_terminal_status(manager, response.run_id)
    final_status = manager.get_status(response.run_id)

    assert terminal_status == WorldBuilderStatus.FAILED
    assert "exceeding the limit" in (final_status.error or "")


def test_run_api_exposes_latest_status() -> None:
    async def fetch_wiki_files(_: str) -> list[WikiFileSummary]:
        return []

    manager = WorldBuilderRunManager(
        model=FakeModel([AIMessage(content="done")]),
        tool_registry=_make_registry(),
        max_steps=8,
        hard_limits=WorldBuilderLimits(max_actors=4, max_state_files=4),
        fetch_wiki_files=fetch_wiki_files,
    )
    client = TestClient(create_app(run_manager=manager))

    start_response = client.post(
        "/api/v1/world-builder/runs",
        json={"session_id": "scenario-1", "scenario": "Brazil joins OPEC"},
    )

    assert start_response.status_code == 200
    payload = start_response.json()
    status_response = client.get(f"/api/v1/world-builder/runs/{payload['run_id']}")
    assert status_response.status_code == 200
    assert status_response.json()["session_id"] == "scenario-1"
    events_response = client.get("/api/v1/world-builder/sessions/scenario-1/events")
    assert events_response.status_code == 200
    assert events_response.json()["events"][0]["event"] == "world_builder.started"
