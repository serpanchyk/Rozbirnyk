"""Translate MCP tools to LangChain objects with strict type mapping."""

from typing import Any, cast

from common.logging import setup_logger
from langchain_core.tools import StructuredTool
from mcp import ClientSession
from pydantic import BaseModel, Field, create_model

logger = setup_logger("mcp_adapter")


class MCPToolAdapter:
    """Transform remote MCP schemas into executable LangChain StructuredTools.

    Data Flow: MCP JSON Schema -> Python Type Mapping
               -> Pydantic Model -> StructuredTool.
    """

    def __init__(self, session: ClientSession) -> None:
        """Initialize the adapter with an active MCP session."""
        self.session = session
        self._type_map = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

    async def fetch_tools(self) -> list[StructuredTool]:
        """Discover and wrap remote tools for the LangChain ecosystem."""
        response = await self.session.list_tools()
        langchain_tools = [self._assemble_tool(tool) for tool in response.tools]

        logger.info("Adapted remote tools", extra={"count": len(langchain_tools)})
        return langchain_tools

    def _assemble_tool(self, mcp_tool: Any) -> StructuredTool:
        """Orchestrate the assembly of a StructuredTool.

        Args:
            mcp_tool: The raw tool metadata from the MCP server.
        """
        args_schema = self._build_args_schema(mcp_tool.name, mcp_tool.inputSchema)

        async def _call_remote(**kwargs: Any) -> Any:
            """Execute remote call with validated arguments."""
            result = await self.session.call_tool(mcp_tool.name, arguments=kwargs)
            return result.content

        return StructuredTool.from_function(
            coroutine=_call_remote,
            name=mcp_tool.name,
            description=mcp_tool.description,
            args_schema=args_schema,
        )

    def _build_args_schema(
        self, tool_name: str, input_schema: dict[str, Any]
    ) -> type[BaseModel]:
        """Construct a Pydantic model based on JSON Schema properties.

        Args:
            tool_name: Name of the tool for model naming.
            input_schema: The JSON Schema provided by the MCP server.
        """
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        fields: dict[str, Any] = {}

        for name, details in properties.items():
            py_type = self._map_mcp_type(details)
            default = ... if name in required else None
            fields[name] = (
                py_type,
                Field(default=default, description=details.get("description")),
            )

        model = create_model(f"{tool_name}Schema", **fields)
        return cast(type[BaseModel], model)

    def _map_mcp_type(self, details: dict[str, Any]) -> Any:
        """Map JSON Schema types to Python types.

        Args:
            details: The property details from the JSON Schema.
        """
        mcp_type = details.get("type", "string")

        if "enum" in details:
            from typing import Literal

            return Literal[tuple(details["enum"])]

        return self._type_map.get(mcp_type, Any)
