from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from telos.db.models import Base
from telos.db.queries.chats import create_chat, get_chat, list_chats, touch_chat
from telos.db.queries.users import get_or_create_development_user
from telos.db.session import create_session_factory, create_sync_engine


def test_user_and_chat_queries_persist_and_scope_records():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        user = get_or_create_development_user(session)
        assert get_or_create_development_user(session).id == user.id
        first = create_chat(session, user.id, "first")
        second = create_chat(session, user.id, "second")

        assert get_chat(session, first.id, user.id).title == "first"
        assert get_chat(session, first.id, second.id) is None
        touch_chat(session, first)
        assert first.updated_at is not None
        assert list_chats(session, user.id)[0].id == first.id


def test_session_factory_uses_non_expiring_sessions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    factory = create_session_factory(engine)
    with factory() as session:
        assert isinstance(session, Session)
        assert session.expire_on_commit is False


def test_sync_engine_enables_connection_pre_ping():
    engine = create_sync_engine("sqlite+pysqlite:///:memory:")
    assert engine.pool._pre_ping is True
