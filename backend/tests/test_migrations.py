import datetime
import os

import pytest
from alembic import command
from alembic.config import Config
from pytest_postgresql import factories
from sqlalchemy import create_engine, text

postgresql_proc_mig = factories.postgresql_proc(port=None)
postgresql_mig = factories.postgresql("postgresql_proc_mig")

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")


def _alembic_cfg(url: str) -> Config:
    os.environ["DATABASE_URL"] = url
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture
def migrated_engine(postgresql_mig):
    info = postgresql_mig.info
    url = f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    yield engine, url
    engine.dispose()


def test_0002_backfills_feed_vehicle_id_from_rt_trip(migrated_engine):
    engine, url = migrated_engine
    cfg = _alembic_cfg(url)

    command.upgrade(cfg, "0001")

    now = datetime.datetime.now(datetime.timezone.utc)
    start_date = datetime.date(2026, 5, 10)

    with engine.begin() as conn:
        # rt_trip has no FK to GTFS tables, so no static fixtures needed.
        # Two vehicles: one linked to rt_trip rows, one orphaned.
        conn.execute(text("""
            INSERT INTO rt_vehicle (vehicle_id, registration_number)
            VALUES (1, 'REG-001'),
                   (2, 'REG-002')
        """))
        # Two trips for vehicle 1 with different timestamps to test "most recent" selection
        conn.execute(text("""
            INSERT INTO rt_trip (trip_id, start_date, vehicle_id, feed_vehicle_id, updated_at)
            VALUES
                ('T1', :sd, 1, 'service-3-REG-001', :now),
                ('T2', :sd, 1, 'service-3-REG-001', :now2)
        """), {"sd": start_date, "now": now, "now2": now - datetime.timedelta(hours=1)})
        # Vehicle 2 has no rt_trip rows → feed_vehicle_id stays NULL after backfill

    command.upgrade(cfg, "0002")

    with engine.connect() as conn:
        rows = {
            r.vehicle_id: r
            for r in conn.execute(text("SELECT * FROM rt_vehicle ORDER BY vehicle_id")).mappings()
        }

    # Vehicle 1: backfilled from most-recent rt_trip (T1, not T2)
    assert rows[1]["feed_vehicle_id"] == "service-3-REG-001"
    assert rows[1]["last_seen_at"] is not None
    assert rows[1]["cache_expires_at"] is not None
    assert rows[1]["cache_expires_at"] > rows[1]["last_seen_at"]

    # Vehicle 2: no rt_trip → feed_vehicle_id remains NULL
    assert rows[2]["feed_vehicle_id"] is None
    # But cache timestamps are still populated
    assert rows[2]["cache_expires_at"] is not None
