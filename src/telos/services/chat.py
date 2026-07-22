"""Asynchronous chat lifecycle and graph invocation boundary."""

import asyncio
from collections.abc import AsyncIterator, Callable
from uuid import UUID
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage

from telos.db.queries.chats import create_chat, get_chat, list_chats, touch_chat
from telos.db.queries.users import get_or_create_development_user


class ChatService:
    def __init__(self, session_factory, graph, callbacks: list[Any] | None = None) -> None:
        self._session_factory = session_factory
        self._graph = graph
        self._callbacks = callbacks or []
        with self._session_factory() as session:
            self.user_id = get_or_create_development_user(session).id

    async def create_chat(self):
        return await asyncio.to_thread(self._with_session, create_chat, self.user_id)

    async def list_chats(self):
        return await asyncio.to_thread(self._with_session, list_chats, self.user_id)

    async def resume_chat(self, chat_id: UUID):
        return await asyncio.to_thread(self._with_session, get_chat, chat_id, self.user_id)

    async def get_messages(self, chat_id: UUID) -> list[BaseMessage]:
        """Return persisted conversation messages for a chat owned by this user."""
        if await self.resume_chat(chat_id) is None:
            raise ValueError("Chat not found")
        state = await self._graph.aget_state(self._graph_config(chat_id))
        return list(state.values.get("messages", []))

    async def send_message(self, chat_id: UUID, content: str) -> AIMessage:
        return await self._consume_stream(chat_id, {"messages": [HumanMessage(content=content)]}, content)

    async def retry(self, chat_id: UUID) -> AIMessage:
        return await self._consume_stream(chat_id, None)

    async def stream_message(
        self, chat_id: UUID, content: str
    ) -> AsyncIterator[AIMessageChunk | AIMessage]:
        """Yield ordered model chunks, then the persisted final assistant message."""
        async for message in self._stream(
            chat_id, {"messages": [HumanMessage(content=content)]}, content
        ):
            yield message

    async def stream_retry(self, chat_id: UUID) -> AsyncIterator[AIMessageChunk | AIMessage]:
        """Yield a retry's chunks, then its persisted final assistant message."""
        async for message in self._stream(chat_id, None):
            yield message

    async def _consume_stream(self, chat_id: UUID, payload: dict[str, Any] | None, title: str | None = None):
        final: AIMessage | None = None
        async for message in self._stream(chat_id, payload, title):
            if isinstance(message, AIMessage):
                final = message
        if final is None:
            raise RuntimeError("Graph did not return an AI message")
        return final

    async def _stream(
        self, chat_id: UUID, payload: dict[str, Any] | None, title: str | None = None
    ) -> AsyncIterator[AIMessageChunk | AIMessage]:
        config = self._graph_config(chat_id)
        async for chunk in self._graph.astream(payload, config, stream_mode="custom"):
            if isinstance(chunk, AIMessageChunk):
                yield chunk
            else:
                yield AIMessageChunk(content=str(chunk))

        state = await self._graph.aget_state(config)
        message = state.values["messages"][-1]
        if not isinstance(message, AIMessage):
            raise RuntimeError("Graph did not return an AI message")
        if title is not None:
            await asyncio.to_thread(self._set_initial_title_and_touch, chat_id, title)
        yield message

    def _with_session(self, query: Callable, *args: Any):
        """Keep short synchronous SQLAlchemy operations out of the event loop."""
        with self._session_factory() as session:
            return query(session, *args)

    def _set_initial_title_and_touch(self, chat_id: UUID, content: str) -> None:
        with self._session_factory() as session:
            chat = get_chat(session, chat_id, self.user_id)
            if chat is not None:
                if chat.title is None:
                    chat.title = content[:80]
                touch_chat(session, chat)

    def _graph_config(self, chat_id: UUID) -> dict[str, Any]:
        """Attach the current application identity to every Langfuse trace."""
        return {
            "configurable": {"thread_id": str(chat_id)},
            "callbacks": self._callbacks,
            "metadata": {
                "langfuse_user_id": str(self.user_id),
                "langfuse_session_id": str(chat_id),
            },
        }
