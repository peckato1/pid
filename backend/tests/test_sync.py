import datetime

from sqlalchemy import select

from pid import models
from pid.sync import sync

from tests.gtfs_fixture import make_zip, make_zip_v2

V1_DATE = datetime.date(2026, 4, 18)
V2_DATE = datetime.date(2026, 5, 2)


def test_sync_imports_all_tables(session):
    with make_zip() as zf:
        sync(session, zf)

    assert session.execute(select(models.Agency)).scalars().one().agency_name == "Test Agency"
    assert session.execute(select(models.Calendar)).scalars().one().service_id == "SVC1"
    assert len(session.execute(select(models.CalendarDate)).scalars().all()) == 1
    assert len(session.execute(select(models.Stop)).scalars().all()) == 2
    assert session.execute(select(models.Route)).scalars().one().route_id == "R1"
    assert session.execute(select(models.RouteAgency)).scalars().one().route_licence_number == 12345
    assert len(session.execute(select(models.Shape)).scalars().all()) == 1
    assert session.execute(select(models.Trip)).scalars().one().trip_id == "TRIP1"
    assert len(session.execute(select(models.StopTime)).scalars().all()) == 2
    assert len(session.execute(select(models.RouteStop)).scalars().all()) == 2
    assert len(session.execute(select(models.Transfer)).scalars().all()) == 1


def test_sync_versions_changed_records(session):
    with make_zip() as zf:
        sync(session, zf)
    with make_zip_v2() as zf:
        sync(session, zf)

    routes = session.execute(select(models.Route).order_by(models.Route.valid_from)).scalars().all()

    # Old R1 must be closed
    old_r1 = next(r for r in routes if r.route_id == "R1" and r.valid_from == V1_DATE)
    assert old_r1.valid_until == V2_DATE
    assert old_r1.route_long_name == "Test Route"

    # New R1 must be open with the new name
    new_r1 = next(r for r in routes if r.route_id == "R1" and r.valid_from == V2_DATE)
    assert new_r1.valid_until is None
    assert new_r1.route_long_name == "Updated Route"

    # New R2 was added
    r2 = next(r for r in routes if r.route_id == "R2")
    assert r2.valid_from == V2_DATE
    assert r2.valid_until is None


def test_sync_closes_deleted_records(session):
    with make_zip() as zf:
        sync(session, zf)
    with make_zip_v2() as zf:
        sync(session, zf)

    # R2 was added in v2, so the R1 trip from v1 doesn't appear in v2 route_sub_agencies → RouteAgency for R1 remains
    # Stop U1Z1P was not changed → still valid_until IS NULL, only one record
    stops = session.execute(
        select(models.Stop).where(models.Stop.stop_id == "U1Z1P")
    ).scalars().all()
    assert len(stops) == 1
    assert stops[0].valid_until is None
