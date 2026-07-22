import asyncio

import httpx
import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from telos.agents.orchestrator.nodes import invoke_llm, is_retryable_llm_error
from telos.agents.orchestrator.prompts import SYSTEM_PROMPT, build_messages


class Model:
    async def astream(self, messages):
        yield AIMessageChunk(content="hello")


def test_llm_node_returns_ai_message(monkeypatch):
    monkeypatch.setattr("telos.agents.orchestrator.nodes.get_stream_writer", lambda: lambda _: None)
    result = asyncio.run(invoke_llm(Model())({"messages": [HumanMessage(content="hi")]}))
    assert result["messages"][0].content == "hello"


def test_prompt_preserves_full_conversation_after_system_message():
    conversation = [HumanMessage(content="first"), AIMessage(content="second")]
    messages = build_messages(conversation)
    assert messages[0].content == SYSTEM_PROMPT
    assert messages[1:] == conversation


def test_llm_node_normalizes_non_ai_message(monkeypatch):
    monkeypatch.setattr("telos.agents.orchestrator.nodes.get_stream_writer", lambda: lambda _: None)
    class OtherMessage:
        content = "normalized"

    class OtherModel:
        async def astream(self, messages):
            yield OtherMessage()

    result = asyncio.run(invoke_llm(OtherModel())({"messages": [HumanMessage(content="hi")]}))
    assert isinstance(result["messages"][0], AIMessage)
    assert result["messages"][0].content == "normalized"


def test_retry_classification():
    assert is_retryable_llm_error(ConnectionError())
    assert not is_retryable_llm_error(ValueError())


@pytest.mark.parametrize("status_code, expected", [(408, True), (429, True), (500, True), (503, True), (400, False), (401, False), (403, False), (422, False)])
def test_retry_classification_for_http_statuses(status_code, expected):
    response = httpx.Response(status_code, request=httpx.Request("POST", "https://example.test"))
    assert is_retryable_llm_error(httpx.HTTPStatusError("failed", request=response.request, response=response)) is expected


def test_retry_classification_handles_transport_timeout_and_status_code_attribute():
    assert is_retryable_llm_error(httpx.ConnectTimeout("timed out"))
    assert is_retryable_llm_error(type("ProviderError", (Exception,), {"status_code": 502})())
    assert not is_retryable_llm_error(type("ProviderError", (Exception,), {"status_code": 413})())
