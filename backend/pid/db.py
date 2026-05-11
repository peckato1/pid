import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from pid.models import Base  # noqa: F401

DATABASE_URL = os.environ["DATABASE_URL"]
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)
async_engine = create_async_engine(ASYNC_DATABASE_URL)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


def get_session() -> Session:
    return Session(engine)
