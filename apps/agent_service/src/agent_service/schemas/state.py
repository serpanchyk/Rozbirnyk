"""Define state passed through the World Builder graph."""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class WorldBuilderState(TypedDict):
    """Carry messages and system context through the World Builder loop."""

    messages: Annotated[list[BaseMessage], add_messages]
    scenario: str
    session_id: str
    remaining_steps: int
