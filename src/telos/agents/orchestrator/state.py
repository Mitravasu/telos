"""Persistent state for the root agent."""

from langgraph.graph import MessagesState


class OrchestratorState(MessagesState):
    """Extensible message state; new fields must have safe defaults."""
