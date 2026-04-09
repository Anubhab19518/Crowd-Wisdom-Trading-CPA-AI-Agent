"""Database helpers and ORM models for demo.
"""
import os
from contextlib import contextmanager
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON

Base = declarative_base()


class Record(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    doc_id = Column(String(128), index=True)
    source = Column(String(64))
    vendor = Column(String(256))
    amount = Column(Float)
    currency = Column(String(16))
    route = Column(String(256))
    date = Column(String(64))
    raw_text = Column(Text)
    record_hash = Column(String(128), unique=True, index=True)
    created_at = Column(DateTime)


class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    payload = Column(JSON)
    created_at = Column(DateTime)


def get_db_path() -> str:
    # default to a local data/agents.db
    root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(root, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(data_dir, "agents.db")}'


_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = get_db_path()
        _engine = create_engine(url, echo=False, future=True)
        _Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(_engine)
    return _engine


@contextmanager
def get_session(engine=None):
    eng = engine or get_engine()
    # ensure sessionmaker initialized
    global _Session
    if _Session is None:
        get_engine()
    session = _Session()
    try:
        yield session
    finally:
        session.close()
