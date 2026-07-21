"""Chat lifecycle and graph invocation boundary."""

from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from telos.db.queries.chats import create_chat, get_chat, list_chats, touch_chat
from telos.db.queries.users import get_or_create_development_user


class ChatService:
    def __init__(self, session_factory, graph) -> None:
        self._session_factory = session_factory
        self._graph = graph
        with self._session_factory() as session:
            self.user_id = get_or_create_development_user(session).id

    def create_chat(self):
        with self._session_factory() as session:
            return create_chat(session, self.user_id)

    def list_chats(self):
        with self._session_factory() as session:
            return list_chats(session, self.user_id)

    def resume_chat(self, chat_id: UUID):
        with self._session_factory() as session:
            return get_chat(session, chat_id, self.user_id)

    def send_message(self, chat_id: UUID, content: str) -> AIMessage:
        result = self._graph.invoke(
            {"messages": [HumanMessage(content=content)]}, {"configurable": {"thread_id": str(chat_id)}}
        )
        message = result["messages"][-1]
        if not isinstance(message, AIMessage):
            raise RuntimeError("Graph did not return an AI message")
        with self._session_factory() as session:
            chat = get_chat(session, chat_id, self.user_id)
            if chat is not None:
                if chat.title is None:
                    chat.title = content[:80]
                touch_chat(session, chat)
        return message

    def retry(self, chat_id: UUID) -> AIMessage:
        result = self._graph.invoke(None, {"configurable": {"thread_id": str(chat_id)}})
        message = result["messages"][-1]
        if not isinstance(message, AIMessage):
            raise RuntimeError("Graph did not return an AI message")
        return message
