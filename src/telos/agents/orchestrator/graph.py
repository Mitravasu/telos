"""Synchronous root-agent graph."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from telos.agents.orchestrator.nodes import invoke_llm, is_retryable_llm_error
from telos.agents.orchestrator.state import OrchestratorState


def build_graph(model: Any, checkpointer: Any):
    builder = StateGraph(OrchestratorState)
    builder.add_node(
        "invoke_llm",
        invoke_llm(model),
        retry_policy=RetryPolicy(max_attempts=3, jitter=True, retry_on=is_retryable_llm_error),
    )
    builder.add_edge(START, "invoke_llm")
    builder.add_edge("invoke_llm", END)
    return builder.compile(checkpointer=checkpointer)
