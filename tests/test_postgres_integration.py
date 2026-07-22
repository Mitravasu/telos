"""Optional end-to-end persistence check; never runs in the default suite."""

import os
import asyncio

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from telos.agents.orchestrator import build_graph
from telos.db.models import Chat
from telos.db.queries.chats import create_chat, get_chat
from telos.db.queries.users import get_or_create_development_user
from telos.db.session import create_session_factory, create_sync_engine


@pytest.mark.integration
def test_application_and_checkpoint_persistence_are_independent():
    url = os.environ.get("TELOS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TELOS_TEST_DATABASE_URL is not configured")

    engine = create_sync_engine(url)
    sessions = create_session_factory(engine)
    with sessions() as session:
        user = get_or_create_development_user(session)
        chat = create_chat(session, user.id, "integration")
        assert get_chat(session, chat.id, user.id).id == chat.id

    class Model:
        async def astream(self, messages):
            yield AIMessage(content="persisted response")

    checkpoint_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    async def invoke_graph():
        async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
            await checkpointer.setup()
            return await build_graph(Model(), checkpointer).ainvoke(
                {"messages": [("user", "hello")]},
                {"configurable": {"thread_id": str(chat.id)}},
            )

    result = asyncio.run(invoke_graph())
    assert result["messages"][-1].content == "persisted response"

    with sessions() as session:
        session.delete(session.get(Chat, chat.id))
        session.commit()


@pytest.mark.integration
def test_cancelled_async_turn_retains_the_user_checkpoint():
    url = os.environ.get("TELOS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("TELOS_TEST_DATABASE_URL is not configured")

    engine = create_sync_engine(url)
    sessions = create_session_factory(engine)
    with sessions() as session:
        user = get_or_create_development_user(session)
        chat = create_chat(session, user.id, "cancelled integration")

    class BlockingModel:
        def __init__(self):
            self.started = asyncio.Event()
            self.cancelled = asyncio.Event()

        async def astream(self, messages):
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
            yield AIMessage(content="unreachable")

    checkpoint_url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def cancel_turn():
        model = BlockingModel()
        async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
            await checkpointer.setup()
            graph = build_graph(model, checkpointer)
            config = {"configurable": {"thread_id": str(chat.id)}}
            task = asyncio.create_task(graph.ainvoke({"messages": [("user", "hello")]}, config))
            await model.started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            state = await graph.aget_state(config)
        return model.cancelled.is_set(), state.values["messages"]

    cancelled, messages = asyncio.run(cancel_turn())

    assert cancelled
    assert [message.content for message in messages] == ["hello"]

    with sessions() as session:
        session.delete(session.get(Chat, chat.id))
        session.commit()
