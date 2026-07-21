"""Orchestrator graph nodes."""

from collections.abc import Callable
import socket
from typing import Any

import httpx
from langchain_core.messages import AIMessage

from telos.agents.orchestrator.prompts import build_messages
from telos.agents.orchestrator.state import OrchestratorState


def is_retryable_llm_error(error: Exception) -> bool:
    """Return whether a provider/transport failure is safe to retry."""
    if isinstance(error, (ConnectionError, TimeoutError, socket.timeout, httpx.TransportError)):
        return True
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {408, 429} or error.response.status_code >= 500
    status_code = getattr(error, "status_code", None)
    return isinstance(status_code, int) and (status_code in {408, 429} or status_code >= 500)


def invoke_llm(model: Any) -> Callable[[OrchestratorState], dict[str, list[AIMessage]]]:
    def node(state: OrchestratorState) -> dict[str, list[AIMessage]]:
        response = model.invoke(build_messages(state["messages"]))
        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response.content))
        return {"messages": [response]}

    return node
