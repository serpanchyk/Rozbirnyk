"""Define common abstractions for LangGraph-backed simulation agents."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Protocol, TypeVar

from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from agent_service.tools.registry import AgentRole, ToolRegistry

StateT = TypeVar("StateT")


class AsyncMessageModel(Protocol):
    """Represent a bound chat model that accepts LangChain messages asynchronously."""

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> BaseMessage:
        """Invoke the model with ordered prompt and conversation messages.

        Args:
            messages: Messages sent to the underlying chat model.

        Returns:
            The model response message.
        """


class ToolBindableModel(Protocol):
    """Represent a chat model that can be bound to role-scoped tools."""

    def bind_tools(self, tools: Sequence[BaseTool]) -> AsyncMessageModel:
        """Bind tools to the model for agent execution.

        Args:
            tools: LangChain tools exposed to the model.

        Returns:
            A model runnable that can be invoked asynchronously.
        """


class AgentBase[StateT](ABC):
    """Provide shared role and tool wiring for simulation agents."""

    role: AgentRole

    def __init__(
        self,
        model: ToolBindableModel,
        tool_registry: ToolRegistry,
        max_steps: int,
    ) -> None:
        """Initialize shared agent dependencies.

        Args:
            model: Chat model that supports LangChain tool binding.
            tool_registry: Registry used to resolve tools for the agent role.
            max_steps: Maximum model turns before the agent stops.
        """
        self._model = model
        self._tool_registry = tool_registry
        self._max_steps = max_steps
        self._tools = tool_registry.resolve_for_role(self.role)
        self._bound_model = model.bind_tools(self._tools)

    @property
    def max_steps(self) -> int:
        """Return the configured maximum model turn count."""
        return self._max_steps

    @property
    def tools(self) -> Sequence[BaseTool]:
        """Return the tools available to this agent."""
        return self._tools

    @abstractmethod
    def create_graph(self) -> CompiledStateGraph[Any, None, Any, Any]:
        """Create a compiled graph for the concrete agent."""
