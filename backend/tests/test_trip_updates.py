import datetime
from unittest.mock import patch

import pytest
from pid.proto import gtfs_realtime_OVapi_pb2, gtfs_realtime_pb2
from sqlalchemy import select

from pid import trip_updates
from pid.models.enums import ScheduleRelationship
from pid.models.realtime import ActualStopTime, TripRun

STOPPED_AT = 1
IN_TRANSIT_TO = 2


def _make_feed():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    return feed


def _add_vehicle(feed, *, entity_id, trip_id, current_stop_sequence, current_status):
    e = feed.entity.add()
    e.id = entity_id
    vp = e.vehicle
    vp.trip.trip_id = trip_id
    vp.current_stop_sequence = current_stop_sequence
    vp.current_status = current_status


def _add_trip_update(
    feed,
    *,
    entity_id,
    trip_id,
    route_id="R1",
    start_date="20260510",
    feed_vehicle_id=None,
    stop_times=(),
):
    """stop_times: iterable of dicts with keys: seq, stop_id, arr, dep, sched_track, act_track, headsign."""
    e = feed.entity.add()
    e.id = entity_id
    tu = e.trip_update
    tu.trip.trip_id = trip_id
    tu.trip.route_id = route_id
    if start_date is not None:
        tu.trip.start_date = start_date
    if feed_vehicle_id is not None:
        tu.vehicle.id = feed_vehicle_id
    for st in stop_times:
        stu = tu.stop_time_update.add()
        stu.stop_sequence = st["seq"]
        stu.stop_id = st["stop_id"]
        if st.get("arr") is not None:
            stu.arrival.delay = st["arr"]
        if st.get("dep") is not None:
            stu.departure.delay = st["dep"]
        ovapi = stu.Extensions[gtfs_realtime_OVapi_pb2.ovapi_stop_time_update]
        if st.get("sched_track"):
            ovapi.scheduled_track = st["sched_track"]
        if st.get("act_track"):
            ovapi.actual_track = st["act_track"]
        if st.get("headsign"):
            ovapi.stop_headsign = st["headsign"]


@pytest.fixture
def patch_golemio():
    """Patches golemio.get to return a response whose content is the supplied FeedMessage bytes."""
    def _install(feed):
        class FakeResponse:
            content = feed.SerializeToString()

            def raise_for_status(self):
                pass

        return patch.object(trip_updates.golemio, "get", return_value=FakeResponse())

    return _install


def test_writes_trip_run_and_stop_times(session, patch_golemio):
    feed = _make_feed()
    _add_vehicle(feed, entity_id="v1", trip_id="T1", current_stop_sequence=2, current_status=STOPPED_AT)
    _add_trip_update(
        feed,
        entity_id="t1",
        trip_id="T1",
        feed_vehicle_id="service-3-1234",
        stop_times=[
            {"seq": 1, "stop_id": "S1", "arr": -10, "dep": 0, "sched_track": "1", "act_track": "1", "headsign": "A"},
            {"seq": 2, "stop_id": "S2", "arr": 30, "dep": 45, "sched_track": "2", "act_track": "3", "headsign": "B"},
            {"seq": 3, "stop_id": "S3", "arr": 60, "dep": 60},
        ],
    )

    with patch_golemio(feed):
        trip_updates.sync(session)

    run = session.execute(select(TripRun)).scalars().one()
    assert run.trip_id == "T1"
    assert run.start_date == datetime.date(2026, 5, 10)
    assert run.feed_vehicle_id == "service-3-1234"
    assert run.schedule_relationship == ScheduleRelationship.SCHEDULED

    stops = session.execute(select(ActualStopTime).order_by(ActualStopTime.stop_sequence)).scalars().all()
    # max_seq=2 (STOPPED_AT), so only seq 1 and 2 are written; seq 3 truncated.
    assert [s.stop_sequence for s in stops] == [1, 2]
    assert stops[0].arrival_delay == -10
    assert stops[0].track_scheduled == "1"
    assert stops[0].track_actual == "1"
    assert stops[0].headsign == "A"
    assert stops[1].track_actual == "3"


def test_in_transit_truncates_one_more(session, patch_golemio):
    """IN_TRANSIT_TO seq=3 means vehicle hasn't reached seq 3 yet, so max_seq=2."""
    feed = _make_feed()
    _add_vehicle(feed, entity_id="v1", trip_id="T1", current_stop_sequence=3, current_status=IN_TRANSIT_TO)
    _add_trip_update(
        feed,
        entity_id="t1",
        trip_id="T1",
        stop_times=[
            {"seq": 1, "stop_id": "S1", "arr": 0, "dep": 0},
            {"seq": 2, "stop_id": "S2", "arr": 0, "dep": 0},
            {"seq": 3, "stop_id": "S3", "arr": 0, "dep": 0},
        ],
    )
    with patch_golemio(feed):
        trip_updates.sync(session)

    stops = session.execute(select(ActualStopTime).order_by(ActualStopTime.stop_sequence)).scalars().all()
    assert [s.stop_sequence for s in stops] == [1, 2]


def test_trip_advances_between_syncs(session, patch_golemio):
    """Vehicle moves forward between two feed fetches: more stop_times appear,
    and delays for already-served stops are updated in place."""
    stops_v1 = [
        {"seq": 1, "stop_id": "S1", "arr": 0, "dep": 5, "act_track": "1"},
        {"seq": 2, "stop_id": "S2", "arr": 30, "dep": 35, "act_track": "2"},
        {"seq": 3, "stop_id": "S3", "arr": 60, "dep": 60},
        {"seq": 4, "stop_id": "S4", "arr": 60, "dep": 60},
    ]
    feed1 = _make_feed()
    _add_vehicle(feed1, entity_id="v1", trip_id="T1", current_stop_sequence=2, current_status=STOPPED_AT)
    _add_trip_update(feed1, entity_id="t1", trip_id="T1", feed_vehicle_id="VEH-1", stop_times=stops_v1)

    with patch_golemio(feed1):
        trip_updates.sync(session)

    stops = session.execute(select(ActualStopTime).order_by(ActualStopTime.stop_sequence)).scalars().all()
    assert [s.stop_sequence for s in stops] == [1, 2]
    assert stops[1].arrival_delay == 30
    assert stops[1].track_actual == "2"
    first_updated_at = session.execute(select(TripRun)).scalars().one().updated_at

    # Second poll: vehicle has advanced to seq 4, and seq 2's actual delay was revised upward.
    stops_v2 = [
        {"seq": 1, "stop_id": "S1", "arr": 0, "dep": 5, "act_track": "1"},
        {"seq": 2, "stop_id": "S2", "arr": 45, "dep": 50, "act_track": "2A"},
        {"seq": 3, "stop_id": "S3", "arr": 50, "dep": 55, "act_track": "3"},
        {"seq": 4, "stop_id": "S4", "arr": 60, "dep": 60, "act_track": "4"},
    ]
    feed2 = _make_feed()
    _add_vehicle(feed2, entity_id="v1", trip_id="T1", current_stop_sequence=4, current_status=STOPPED_AT)
    _add_trip_update(feed2, entity_id="t1", trip_id="T1", feed_vehicle_id="VEH-1", stop_times=stops_v2)

    with patch_golemio(feed2):
        trip_updates.sync(session)

    # Still one TripRun (merged on PK), updated_at advanced.
    runs = session.execute(select(TripRun)).scalars().all()
    assert len(runs) == 1
    assert runs[0].updated_at > first_updated_at

    stops = session.execute(select(ActualStopTime).order_by(ActualStopTime.stop_sequence)).scalars().all()
    assert [s.stop_sequence for s in stops] == [1, 2, 3, 4]
    # Revised delay/track for seq 2 was applied in place.
    assert stops[1].arrival_delay == 45
    assert stops[1].departure_delay == 50
    assert stops[1].track_actual == "2A"
    # Newly-served stops were inserted.
    assert stops[2].arrival_delay == 50
    assert stops[3].track_actual == "4"


def test_skips_trip_without_vehicle_position(session, patch_golemio):
    feed = _make_feed()
    # No VehiclePosition for T1
    _add_trip_update(
        feed,
        entity_id="t1",
        trip_id="T1",
        stop_times=[{"seq": 1, "stop_id": "S1", "arr": 0, "dep": 0}],
    )
    with patch_golemio(feed):
        trip_updates.sync(session)

    assert session.execute(select(TripRun)).scalars().all() == []
    assert session.execute(select(ActualStopTime)).scalars().all() == []
