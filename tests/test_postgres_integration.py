"""Optional end-to-end persistence check; never runs in the default suite."""

import os

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver

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
        def invoke(self, messages):
            return AIMessage(content="persisted response")

    checkpoint_url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    with PostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        checkpointer.setup()
        result = build_graph(Model(), checkpointer).invoke(
            {"messages": [("user", "hello")]}, {"configurable": {"thread_id": str(chat.id)}}
        )
    assert result["messages"][-1].content == "persisted response"

    with sessions() as session:
        session.delete(session.get(Chat, chat.id))
        session.commit()
