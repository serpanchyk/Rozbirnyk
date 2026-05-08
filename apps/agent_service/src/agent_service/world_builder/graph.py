"""Build the LangGraph ReAct loop for World Builder initialization."""

from collections.abc import Sequence
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode

from agent_service.tools.registry import AgentRole, ToolRegistry
from agent_service.world_builder.prompts import WORLD_BUILDER_SYSTEM_PROMPT
from agent_service.world_builder.state import WorldBuilderState

DEFAULT_MAX_STEPS = 8


def create_world_builder_graph(
    model: Any,
    tool_registry: ToolRegistry,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> Any:
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
    tools = tool_registry.resolve_for_role(AgentRole.WORLD_BUILDER)
    if not hasattr(model, "bind_tools"):
        msg = "World Builder model must expose bind_tools"
        raise TypeError(msg)
    bound_model = model.bind_tools(tools)

    async def model_node(state: WorldBuilderState) -> dict[str, list[BaseMessage] | int]:
        """Invoke the model with the system prompt and current graph messages."""
        remaining_steps = state.get("remaining_steps", max_steps)
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

        prompt_messages = _build_prompt_messages(state)
        response = await bound_model.ainvoke(prompt_messages)
        return {"messages": [response], "remaining_steps": remaining_steps - 1}

    graph = StateGraph(WorldBuilderState)
    graph.add_node("model", model_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", _route_after_model)
    graph.add_edge("tools", "model")
    return graph.compile()


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
    return {
        "messages": list(messages or [HumanMessage(content=f"What if {scenario}")]),
        "scenario": scenario,
        "session_id": session_id,
        "remaining_steps": remaining_steps,
    }


def _build_prompt_messages(state: WorldBuilderState) -> list[BaseMessage]:
    """Return model input messages with system instructions first."""
    messages = state.get("messages", [])
    user_messages: list[BaseMessage]
    if messages:
        user_messages = list(messages)
    else:
        user_messages = [HumanMessage(content=f"What if {state['scenario']}")]
    return [SystemMessage(content=WORLD_BUILDER_SYSTEM_PROMPT), *user_messages]


def _route_after_model(state: WorldBuilderState) -> Literal["tools", "__end__"]:
    """Route to tools when the latest model message requested tool calls."""
    if state.get("remaining_steps", 0) <= 0:
        return "__end__"
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    return "tools" if tool_calls else "__end__"
