import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
import pytest

from telos.services.chat import ChatService


class FakeGraph:
    def __init__(self):
        self.calls = []
        self.message = AIMessage(content="reply")

    async def astream(self, payload, config, stream_mode):
        self.calls.append((payload, config, stream_mode))
        yield AIMessageChunk(content="rep")
        yield AIMessageChunk(content="ly")

    async def aget_state(self, _):
        return SimpleNamespace(values={"messages": [self.message]})


def make_service(monkeypatch, graph, session=object(), user_id=None):
    user_id = user_id or uuid4()
    monkeypatch.setattr("telos.services.chat.get_or_create_development_user", lambda _: SimpleNamespace(id=user_id))
    return ChatService(lambda: nullcontext(session), graph), user_id


def test_stream_message_uses_thread_and_emits_ordered_chunks_then_final(monkeypatch):
    user_id, chat_id = uuid4(), uuid4()
    session = object()
    monkeypatch.setattr("telos.services.chat.get_or_create_development_user", lambda _: SimpleNamespace(id=user_id))
    monkeypatch.setattr("telos.services.chat.get_chat", lambda *_: None)
    handler = object()
    graph = FakeGraph()
    service = ChatService(lambda: nullcontext(session), graph, callbacks=[handler])

    async def exercise():
        return [message async for message in service.stream_message(chat_id, "hello")]

    messages = asyncio.run(exercise())
    payload, config, mode = graph.calls[0]
    assert [message.content for message in messages] == ["rep", "ly", "reply"]
    assert isinstance(messages[-1], AIMessage)
    assert payload["messages"][0].content == "hello"
    assert config["configurable"]["thread_id"] == str(chat_id)
    assert config["callbacks"] == [handler]
    assert config["metadata"] == {
        "langfuse_user_id": str(user_id),
        "langfuse_session_id": str(chat_id),
    }
    assert mode == "custom"


def test_send_message_sets_initial_title_and_returns_final(monkeypatch):
    chat_id = uuid4()
    chat = SimpleNamespace(title=None)
    graph = FakeGraph()
    monkeypatch.setattr("telos.services.chat.get_chat", lambda *_: chat)
    touched = []
    monkeypatch.setattr("telos.services.chat.touch_chat", lambda _, value: touched.append(value))
    service, _ = make_service(monkeypatch, graph)

    response = asyncio.run(service.send_message(chat_id, "a useful opening message"))

    assert response.content == "reply"
    assert chat.title == "a useful opening message"
    assert touched == [chat]


def test_service_delegates_async_chat_lifecycle_queries(monkeypatch):
    graph = FakeGraph()
    service, user_id = make_service(monkeypatch, graph)
    created, listed, resumed = object(), [object()], object()
    monkeypatch.setattr("telos.services.chat.create_chat", lambda _, user: (created, user))
    monkeypatch.setattr("telos.services.chat.list_chats", lambda _, user: (listed, user))
    monkeypatch.setattr("telos.services.chat.get_chat", lambda _, chat, user: (resumed, chat, user))

    async def exercise():
        return (
            await service.create_chat(),
            await service.list_chats(),
            await service.resume_chat(uuid4()),
        )

    created_result, listed_result, resumed_result = asyncio.run(exercise())
    assert created_result == (created, user_id)
    assert listed_result == (listed, user_id)
    assert resumed_result[0] is resumed
    assert resumed_result[2] == user_id


@pytest.mark.parametrize("method, payload", [("send_message", "hello"), ("retry", None)])
def test_service_rejects_non_ai_graph_response(monkeypatch, method, payload):
    graph = FakeGraph()
    graph.message = HumanMessage(content="not an answer")
    service, _ = make_service(monkeypatch, graph)

    with pytest.raises(RuntimeError, match="AI message"):
        if payload is None:
            asyncio.run(service.retry(uuid4()))
        else:
            asyncio.run(service.send_message(uuid4(), payload))


def test_retry_reuses_thread_without_a_new_user_message(monkeypatch):
    graph = FakeGraph()
    service, _ = make_service(monkeypatch, graph)
    chat_id = uuid4()

    assert asyncio.run(service.retry(chat_id)).content == "reply"
    assert graph.calls == [
        (
            None,
            {
                "configurable": {"thread_id": str(chat_id)},
                "callbacks": [],
                "metadata": {
                    "langfuse_user_id": str(service.user_id),
                    "langfuse_session_id": str(chat_id),
                },
            },
            "custom",
        )
    ]


def test_cancellation_propagates_without_a_final_message(monkeypatch):
    class BlockingGraph:
        async def astream(self, *_args, **_kwargs):
            await asyncio.Event().wait()
            yield AIMessageChunk(content="late")

    service, _ = make_service(monkeypatch, BlockingGraph())

    async def exercise():
        task = asyncio.create_task(service.send_message(uuid4(), "hello"))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())


def test_cancellation_closes_the_graph_stream(monkeypatch):
    class TrackedStream:
        def __init__(self):
            self.started = asyncio.Event()
            self.closed = asyncio.Event()

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.started.set()
            await asyncio.Event().wait()
            raise StopAsyncIteration

        async def aclose(self):
            self.closed.set()

    class Graph:
        def __init__(self):
            self.stream = TrackedStream()

        def astream(self, *_args, **_kwargs):
            return self.stream

    graph = Graph()
    service, _ = make_service(monkeypatch, graph)

    async def exercise():
        task = asyncio.create_task(service.send_message(uuid4(), "hello"))
        await graph.stream.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    assert graph.stream.closed.is_set()
