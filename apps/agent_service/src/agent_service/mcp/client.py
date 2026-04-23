"""Handle network communication with remote MCP servers via SSE."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from common.logging import setup_logger
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = setup_logger("mcp_client")


class RemoteMCPClient:
    """Manage lifecycle of SSE connections to external MCP microservices."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize connection parameters.

        Args:
            host: The network hostname of the target service.
            port: The port where the SSE server is exposed.
        """
        self.url = f"http://{host}:{port}/sse"

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[ClientSession, None]:
        """Establish and maintain an active MCP session.

        Yields:
            An initialized ClientSession ready for interaction.
        """
        logger.info("Connecting to MCP server", extra={"url": self.url})
        try:
            async with sse_client(url=self.url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    yield session
        except Exception as e:
            logger.error(
                "MCP connection failed", extra={"error": str(e), "url": self.url}
            )
            raise
