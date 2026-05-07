"""Test Wiki Service API routes and MCP tool wrappers."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from wiki_service import main
from wiki_service.main import create_app
from wiki_service.manager import WikiManager


@pytest.fixture
def test_manager(tmp_path):
    """Create a temporary manager for API and tool tests."""
    return WikiManager(tmp_path)


@pytest.fixture
def client(test_manager):
    """Create a FastAPI test client for the Wiki Service."""
    return TestClient(create_app(test_manager))


def test_reset_and_timeline_api(client):
    """Verify reset and timeline endpoints work together."""
    response = client.post("/api/v1/wiki/reset", json={"session_id": "scenario-1"})

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "scenario-1",
        "message": "Wiki session reset.",
    }

    timeline = client.get("/api/v1/wiki/timeline", params={"session_id": "scenario-1"})
    assert timeline.status_code == 200
    assert timeline.json()["content"] == "# Timeline\n\n"


def test_files_api_returns_metadata(client, test_manager):
    """Verify files endpoint returns metadata for wiki files."""
    asyncio.run(
        test_manager.edit_state_file(
            "economy.md",
            "# Economy\nShort Description: Baseline.\n",
            "scenario-1",
        )
    )

    response = client.get("/api/v1/wiki/files", params={"session_id": "scenario-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "scenario-1"
    assert {
        "path": "States/economy.md",
        "title": "Economy",
        "short_description": "Baseline.",
        "kind": "state",
    } in payload["files"]


def test_actor_files_api_returns_content(client, test_manager):
    """Verify actor files endpoint returns metadata and actor content."""
    content = "# Actor\nShort Description: Participant.\n"
    asyncio.run(test_manager.edit_actor_file("actor", content, "scenario-1"))

    response = client.get(
        "/api/v1/wiki/actors/actor/files",
        params={"session_id": "scenario-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contents"] == {"Actors/actor.md": content}
    assert payload["files"][0]["path"] == "Actors/actor.md"


def test_export_api_returns_zip(client, test_manager):
    """Verify export endpoint returns zip bytes."""
    asyncio.run(test_manager.edit_state_file("economy.md", "# Economy\n", "scenario-1"))

    response = client.get("/api/v1/wiki/export", params={"session_id": "scenario-1"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content.startswith(b"PK")


@pytest.mark.asyncio
async def test_mcp_tool_wrappers_use_shared_manager(monkeypatch, test_manager):
    """Verify MCP tool functions delegate to the configured shared manager."""
    monkeypatch.setattr(main, "manager", test_manager)

    await main.edit_state_file("economy.md", "# Economy\n", "scenario-1")
    await main.edit_actor_file("actor", "# Actor\n", "scenario-1")
    timeline = await main.append_to_timeline("- Day 1", "scenario-1")
    actor = await main.append_to_actor_memory("actor", "- Memory", "scenario-1")

    assert "# Economy\n" == await main.read_state_file("economy.md", "scenario-1")
    assert "- Day 1" in timeline
    assert "- Memory" in actor
    assert "Deleted States/economy.md" == await main.delete_file(
        "States/economy.md",
        "scenario-1",
    )
