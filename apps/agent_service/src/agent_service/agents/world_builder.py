"""Build the LangGraph ReAct loop for World Builder initialization."""

from collections.abc import Sequence
from typing import Literal, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode

from agent_service.agents.base import AgentBase, ToolBindableModel
from agent_service.prompts.world_builder import WORLD_BUILDER_SYSTEM_PROMPT
from agent_service.schemas.state import WorldBuilderState
from agent_service.tools.registry import AgentRole, ToolRegistry

DEFAULT_MAX_STEPS = 8


class WorldBuilder(AgentBase[WorldBuilderState]):
    """Initialize a scenario's Wiki through a role-scoped ReAct loop."""

    role = AgentRole.WORLD_BUILDER

    def __init__(
        self,
        model: object,
        tool_registry: ToolRegistry,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        """Initialize the World Builder agent.

        Args:
            model: Chat model or runnable exposing `bind_tools`.
            tool_registry: Registry used to resolve World Builder capabilities.
            max_steps: Maximum model turns before the graph terminates.
        """
        if not hasattr(model, "bind_tools"):
            msg = "World Builder model must expose bind_tools"
            raise TypeError(msg)
        super().__init__(
            model=cast(ToolBindableModel, model),
            tool_registry=tool_registry,
            max_steps=max_steps,
        )

    def create_graph(
        self,
    ) -> CompiledStateGraph[
        WorldBuilderState,
        None,
        WorldBuilderState,
        WorldBuilderState,
    ]:
        """Create a compiled World Builder graph with role-scoped tools.

        Returns:
            A compiled LangGraph workflow.
        """
        graph = StateGraph(WorldBuilderState)
        graph.add_node("model", self._model_node)
        graph.add_node("tools", ToolNode(list(self.tools)))
        graph.add_edge(START, "model")
        graph.add_conditional_edges("model", self._route_after_model)
        graph.add_edge("tools", "model")
        return cast(
            CompiledStateGraph[
                WorldBuilderState,
                None,
                WorldBuilderState,
                WorldBuilderState,
            ],
            graph.compile(),
        )

    def build_initial_state(
        self,
        scenario: str,
        session_id: str,
        messages: Sequence[BaseMessage] | None = None,
        remaining_steps: int | None = None,
    ) -> WorldBuilderState:
        """Create an initial graph state for a scenario.

        Args:
            scenario: User's What-if scenario.
            session_id: Wiki session identifier controlled by the system.
            messages: Optional initial conversation messages.
            remaining_steps: Maximum model turns before termination.

        Returns:
            Initial state accepted by the compiled World Builder graph.
        """
        initial_remaining_steps = remaining_steps
        if initial_remaining_steps is None:
            initial_remaining_steps = self.max_steps
        return self.build_state(
            scenario=scenario,
            session_id=session_id,
            messages=messages,
            remaining_steps=initial_remaining_steps,
        )

    @staticmethod
    def build_state(
        scenario: str,
        session_id: str,
        messages: Sequence[BaseMessage] | None = None,
        remaining_steps: int = DEFAULT_MAX_STEPS,
    ) -> WorldBuilderState:
        """Create a World Builder state payload.

        Args:
            scenario: User's What-if scenario.
            session_id: Wiki session identifier controlled by the system.
            messages: Optional initial conversation messages.
            remaining_steps: Maximum model turns before termination.

        Returns:
            Initial state accepted by the compiled World Builder graph.
        """
        return {
            "messages": list(messages or [HumanMessage(content=f"What if {scenario}")]),
            "scenario": scenario,
            "session_id": session_id,
            "remaining_steps": remaining_steps,
        }

    async def _model_node(
        self,
        state: WorldBuilderState,
    ) -> dict[str, list[BaseMessage] | int]:
        """Invoke the model with the system prompt and current graph messages."""
        remaining_steps = state.get("remaining_steps", self.max_steps)
        if remaining_steps <= 0:
            return {
                "messages": [
                    AIMessage(
                        content=(
                            "World Builder stopped because the configured step limit was reached."
                        )
                    )
                ],
                "remaining_steps": 0,
            }

        prompt_messages = self._build_prompt_messages(state)
        response = await self._bound_model.ainvoke(prompt_messages)
        return {"messages": [response], "remaining_steps": remaining_steps - 1}

    def _build_prompt_messages(self, state: WorldBuilderState) -> list[BaseMessage]:
        """Return model input messages with system instructions first."""
        messages = state.get("messages", [])
        user_messages: list[BaseMessage]
        if messages:
            user_messages = list(messages)
        else:
            user_messages = [HumanMessage(content=f"What if {state['scenario']}")]
        return [SystemMessage(content=WORLD_BUILDER_SYSTEM_PROMPT), *user_messages]

    def _route_after_model(self, state: WorldBuilderState) -> Literal["tools", "__end__"]:
        """Route to tools when the latest model message requested tool calls."""
        if state.get("remaining_steps", 0) <= 0:
            return "__end__"
        messages = state.get("messages", [])
        if not messages:
            return "__end__"
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None)
        return "tools" if tool_calls else "__end__"


def create_world_builder_graph(
    model: object,
    tool_registry: ToolRegistry,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> CompiledStateGraph[
    WorldBuilderState,
    None,
    WorldBuilderState,
    WorldBuilderState,
]:
    """Create a compiled World Builder graph with role-scoped tools.

    Args:
        model: Chat model or runnable exposing `bind_tools`.
        tool_registry: Registry used to resolve World Builder capabilities.
        max_steps: Maximum model turns before the graph terminates.

    Returns:
        A compiled LangGraph workflow.

    Raises:
        TypeError: If the provided model cannot bind LangChain tools.
    """
    return WorldBuilder(
        model=model,
        tool_registry=tool_registry,
        max_steps=max_steps,
    ).create_graph()


def build_world_builder_initial_state(
    scenario: str,
    session_id: str,
    messages: Sequence[BaseMessage] | None = None,
    remaining_steps: int = DEFAULT_MAX_STEPS,
) -> WorldBuilderState:
    """Create an initial graph state for a scenario.

    Args:
        scenario: User's What-if scenario.
        session_id: Wiki session identifier controlled by the system.
        messages: Optional initial conversation messages.
        remaining_steps: Maximum model turns before termination.

    Returns:
        Initial state accepted by the compiled World Builder graph.
    """
    return WorldBuilder.build_state(
        scenario=scenario,
        session_id=session_id,
        messages=messages,
        remaining_steps=remaining_steps,
    )
