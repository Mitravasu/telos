from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_sync_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine):
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
