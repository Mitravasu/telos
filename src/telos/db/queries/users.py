from sqlalchemy import select
from sqlalchemy.orm import Session

from telos.db.models import User


def get_or_create_development_user(session: Session) -> User:
    user = session.scalar(select(User).where(User.email == "developer@telos.local"))
    if user is None:
        user = User(first_name="Development", last_name="User", email="developer@telos.local")
        session.add(user)
        session.commit()
    return user
