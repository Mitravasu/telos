from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage

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
