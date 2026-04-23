"""Unit tests for the MCPToolAdapter translation layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_service.mcp.adapter import MCPToolAdapter
from langchain_core.tools import StructuredTool
from pydantic import BaseModel


@pytest.fixture
def mock_session():
    """Provide a mocked MCP ClientSession with a standard tool schema."""
    session = AsyncMock()

    mock_tool = MagicMock()
    mock_tool.name = "get_weather"
    mock_tool.description = "Fetch current weather"
    mock_tool.inputSchema = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
    }

    mock_response = MagicMock()
    mock_response.tools = [mock_tool]
    session.list_tools.return_value = mock_response

    return session


@pytest.mark.asyncio
async def test_fetch_tools_assembly(mock_session):
    """Verify that MCP tools are correctly assembled into StructuredTools."""
    adapter = MCPToolAdapter(mock_session)
    tools = await adapter.fetch_tools()

    assert len(tools) == 1
    assert isinstance(tools[0], StructuredTool)
    assert tools[0].name == "get_weather"

    args_schema = tools[0].args_schema
    assert isinstance(args_schema, type)
    assert issubclass(args_schema, BaseModel)


@pytest.mark.asyncio
async def test_tool_execution_argument_passing(mock_session):
    """Verify assembled tool correctly passes arguments to the session.

    Ensures LangChain invocation maps inputs to MCP call_tool arguments.
    """
    adapter = MCPToolAdapter(mock_session)
    tools = await adapter.fetch_tools()
    tool = tools[0]

    mock_result = MagicMock()
    mock_result.content = {"temp": 20}
    mock_session.call_tool.return_value = mock_result

    result = await tool.ainvoke({"location": "Lviv", "unit": "celsius"})

    assert result == {"temp": 20}
    mock_session.call_tool.assert_awaited_once_with(
        "get_weather", arguments={"location": "Lviv", "unit": "celsius"}
    )


def test_map_mcp_type_robustness():
    """Verify the internal type mapper handles various types correctly."""
    adapter = MCPToolAdapter(AsyncMock())

    assert adapter._map_mcp_type({"type": "integer"}) is int
    assert adapter._map_mcp_type({"type": "boolean"}) is bool

    enum_details = {"type": "string", "enum": ["active", "pending"]}
    mapped_type = adapter._map_mcp_type(enum_details)

    assert "active" in mapped_type.__args__
    assert "pending" in mapped_type.__args__


@pytest.mark.asyncio
async def test_build_args_schema_requirements(mock_session):
    """Verify generated model correctly identifies required fields."""
    adapter = MCPToolAdapter(mock_session)

    input_schema = {
        "properties": {"req": {"type": "string"}, "opt": {"type": "string"}},
        "required": ["req"],
    }

    model = adapter._build_args_schema("test_tool", input_schema)

    assert model.model_fields["req"].is_required() is True
    assert model.model_fields["opt"].is_required() is False
