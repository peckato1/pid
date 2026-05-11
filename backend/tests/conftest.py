import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from pid.models import Base

postgresql_proc = factories.postgresql_proc()
postgresql = factories.postgresql("postgresql_proc")


@pytest.fixture
def session(postgresql):
    info = postgresql.info
    url = f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()
