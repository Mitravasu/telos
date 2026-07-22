from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage
import pytest

from telos.services.chat import ChatService


class FakeGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, payload, config):
        self.calls.append((payload, config))
        return {"messages": [AIMessage(content="reply")]}


def test_send_message_uses_chat_id_as_graph_thread(monkeypatch):
    user_id, chat_id = uuid4(), uuid4()
    session = object()
    monkeypatch.setattr("telos.services.chat.get_or_create_development_user", lambda _: SimpleNamespace(id=user_id))
    monkeypatch.setattr("telos.services.chat.get_chat", lambda *_: None)
    service = ChatService(lambda: nullcontext(session), FakeGraph())

    response = service.send_message(chat_id, "hello")

    assert response.content == "reply"
    payload, config = service._graph.calls[0]
    assert payload["messages"][0].content == "hello"
    assert config["configurable"]["thread_id"] == str(chat_id)


def make_service(monkeypatch, graph, session=object(), user_id=None):
    user_id = user_id or uuid4()
    monkeypatch.setattr("telos.services.chat.get_or_create_development_user", lambda _: SimpleNamespace(id=user_id))
    return ChatService(lambda: nullcontext(session), graph), user_id


def test_send_message_sets_initial_title_and_touches_chat(monkeypatch):
    chat_id = uuid4()
    chat = SimpleNamespace(title=None)
    graph = FakeGraph()
    monkeypatch.setattr("telos.services.chat.get_chat", lambda *_: chat)
    touched = []
    monkeypatch.setattr("telos.services.chat.touch_chat", lambda _, value: touched.append(value))
    service, _ = make_service(monkeypatch, graph)

    service.send_message(chat_id, "a useful opening message")

    assert chat.title == "a useful opening message"
    assert touched == [chat]


def test_service_delegates_chat_lifecycle_queries(monkeypatch):
    graph = FakeGraph()
    service, user_id = make_service(monkeypatch, graph)
    created, listed, resumed = object(), [object()], object()
    monkeypatch.setattr("telos.services.chat.create_chat", lambda _, user: (created, user))
    monkeypatch.setattr("telos.services.chat.list_chats", lambda _, user: (listed, user))
    monkeypatch.setattr("telos.services.chat.get_chat", lambda _, chat, user: (resumed, chat, user))

    assert service.create_chat() == (created, user_id)
    assert service.list_chats() == (listed, user_id)
    assert service.resume_chat(uuid4())[0] is resumed


@pytest.mark.parametrize("method, payload", [("send_message", "hello"), ("retry", None)])
def test_service_rejects_non_ai_graph_response(monkeypatch, method, payload):
    class InvalidGraph:
        def invoke(self, *_):
            return {"messages": [HumanMessage(content="not an answer")]}

    from langchain_core.messages import HumanMessage

    service, _ = make_service(monkeypatch, InvalidGraph())
    with pytest.raises(RuntimeError, match="AI message"):
        if payload is None:
            service.retry(uuid4())
        else:
            service.send_message(uuid4(), payload)


def test_retry_reuses_thread_without_a_new_user_message(monkeypatch):
    graph = FakeGraph()
    service, _ = make_service(monkeypatch, graph)
    chat_id = uuid4()

    assert service.retry(chat_id).content == "reply"
    assert graph.calls == [(None, {"configurable": {"thread_id": str(chat_id)}})]
