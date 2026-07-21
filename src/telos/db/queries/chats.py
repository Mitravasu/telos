from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from telos.db.models import Chat


def create_chat(session: Session, user_id: UUID, title: str | None = None) -> Chat:
    chat = Chat(user_id=user_id, title=title)
    session.add(chat)
    session.commit()
    return chat


def list_chats(session: Session, user_id: UUID, limit: int = 20) -> list[Chat]:
    return list(
        session.scalars(
            select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc()).limit(limit)
        )
    )


def get_chat(session: Session, chat_id: UUID, user_id: UUID) -> Chat | None:
    return session.scalar(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))


def touch_chat(session: Session, chat: Chat) -> None:
    chat.updated_at = datetime.now(timezone.utc)
    session.add(chat)
    session.commit()
