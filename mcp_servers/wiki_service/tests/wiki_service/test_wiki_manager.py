"""Test filesystem behavior for the WikiManager."""

from io import BytesIO
from zipfile import ZipFile

import pytest
from wiki_service.manager import WikiManager


@pytest.fixture
def manager(tmp_path):
    """Create a WikiManager backed by a temporary directory."""
    return WikiManager(tmp_path)


@pytest.mark.asyncio
async def test_reset_creates_session_structure(manager):
    """Verify reset creates the required wiki files and directories."""
    await manager.reset("scenario-1")

    assert await manager.read_timeline("scenario-1") == "# Timeline\n\n"


@pytest.mark.asyncio
async def test_edit_and_read_state_file(manager):
    """Verify state files can be created and read through normalized paths."""
    content = "# Economy\nShort Description: Economic baseline.\n"

    result = await manager.edit_state_file("economy.md", content, "scenario-1")

    assert result == content
    assert await manager.read_state_file("States/economy.md", "scenario-1") == content


@pytest.mark.asyncio
async def test_edit_and_read_actor_file(manager):
    """Verify actor files can be created and read by actor identifier."""
    content = "# Prime Minister\nShort Description: National executive.\n"

    result = await manager.edit_actor_file("prime_minister", content, "scenario-1")

    assert result == content
    assert await manager.read_actor_file("prime_minister", "scenario-1") == content


@pytest.mark.asyncio
async def test_append_to_timeline(manager):
    """Verify timeline appends preserve existing content."""
    await manager.reset("scenario-1")

    content = await manager.append_to_timeline("- Day 1: Event.", "scenario-1")

    assert content == "# Timeline\n\n\n- Day 1: Event.\n"


@pytest.mark.asyncio
async def test_append_to_actor_memory_creates_section(manager):
    """Verify actor memory appends create the memory section when missing."""
    await manager.edit_actor_file(
        "actor",
        "# Actor\nShort Description: Test actor.\n",
        "scenario-1",
    )

    content = await manager.append_to_actor_memory("actor", "- Remembers event.", "scenario-1")

    assert "## Private Memory" in content
    assert "- Remembers event." in content


@pytest.mark.asyncio
async def test_list_files_parses_markdown_metadata(manager):
    """Verify file metadata uses Markdown title and short description."""
    await manager.edit_state_file(
        "economy.md",
        "# Economy\nShort Description: Baseline.\n",
        "scenario-1",
    )
    await manager.edit_actor_file(
        "actor",
        "# Actor\nShort Description: Participant.\n",
        "scenario-1",
    )

    files = await manager.list_files("scenario-1")

    metadata = {file.path: file for file in files}
    assert metadata["States/economy.md"].title == "Economy"
    assert metadata["States/economy.md"].short_description == "Baseline."
    assert metadata["Actors/actor.md"].kind == "actor"


@pytest.mark.asyncio
async def test_get_actor_files_returns_actor_content(manager):
    """Verify actor context injection returns actor metadata and content."""
    content = "# Actor\nShort Description: Participant.\n"
    await manager.edit_actor_file("actor", content, "scenario-1")

    files, contents = await manager.get_actor_files("actor", "scenario-1")

    assert files[0].path == "Actors/actor.md"
    assert contents == {"Actors/actor.md": content}


@pytest.mark.asyncio
async def test_delete_file_rejects_timeline(manager):
    """Verify Timeline.md cannot be deleted through the manager."""
    await manager.reset("scenario-1")

    with pytest.raises(ValueError, match="Timeline"):
        await manager.delete_file("Timeline.md", "scenario-1")


@pytest.mark.asyncio
async def test_delete_file_removes_state_file(manager):
    """Verify delete_file removes a non-timeline Markdown file."""
    await manager.edit_state_file("obsolete.md", "# Obsolete\n", "scenario-1")

    await manager.delete_file("States/obsolete.md", "scenario-1")

    with pytest.raises(FileNotFoundError):
        await manager.read_state_file("obsolete.md", "scenario-1")


@pytest.mark.asyncio
async def test_rejects_paths_that_escape_session(manager):
    """Verify parent directory traversal is rejected."""
    with pytest.raises(ValueError, match="parent"):
        await manager.edit_state_file("../escape.md", "# Escape\n", "scenario-1")


@pytest.mark.asyncio
async def test_export_session_contains_wiki_files(manager):
    """Verify export returns a zip containing session files."""
    await manager.edit_state_file("economy.md", "# Economy\n", "scenario-1")

    archive = await manager.export_session("scenario-1")

    with ZipFile(BytesIO(archive)) as zip_file:
        assert sorted(zip_file.namelist()) == [
            "States/economy.md",
            "Timeline.md",
        ]
