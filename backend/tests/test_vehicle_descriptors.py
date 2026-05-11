import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from pid import vehicle_descriptors
from pid.models.enums import RouteType
from pid.models.realtime import ActualStopTime, Operator, TripRun, Vehicle, VehicleType
from pid.models.route import Route
from pid.models.trip import Trip

START_DATE = datetime.date(2026, 5, 10)
VALID_FROM = datetime.date(2026, 4, 18)


def _seed(session, *, trip_id="T1", route_type=RouteType.BUS, feed_vehicle_id="VEH-1", active=True):
    session.merge(Route(route_id="R1", route_type=route_type, valid_from=VALID_FROM))
    session.add(Trip(trip_id=trip_id, route_id="R1", service_id="SVC1", valid_from=VALID_FROM))
    session.add(TripRun(trip_id=trip_id, start_date=START_DATE, feed_vehicle_id=feed_vehicle_id))
    session.flush()
    if active:
        ast = ActualStopTime(trip_id=trip_id, start_date=START_DATE, stop_sequence=1, stop_id="S1")
        session.add(ast)
        session.flush()
        ast.updated_at = datetime.datetime.now(datetime.timezone.utc)
    session.commit()


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def patch_get():
    def _install(responses):
        if not isinstance(responses, list):
            responses = [responses]
        it = iter(responses)
        return patch.object(vehicle_descriptors.golemio, "get", side_effect=lambda *a, **kw: next(it))
    return _install


VD_PAYLOAD = {
    "origin_route_name": "100",
    "run_number": 42,
    "vehicle_descriptor": {
        "vehicle_registration_number": "REG-001",
        "vehicle_type": "Citybus 12M",
        "operator": "DPP",
        "is_wheelchair_accessible": True,
        "is_air_conditioned": True,
        "has_usb_chargers": False,
    },
}


def test_enriches_candidate(session, patch_get):
    _seed(session)
    with patch_get(FakeResponse(200, VD_PAYLOAD)):
        vehicle_descriptors.enrich(session)

    run = session.execute(select(TripRun)).scalars().one()
    vehicle = session.execute(select(Vehicle)).scalars().one()
    assert run.vehicle_id == vehicle.vehicle_id
    assert run.origin_route_name == "100"
    assert run.run_number == 42
    assert vehicle.registration_number == "REG-001"
    assert vehicle.usb_chargers is False
    assert session.execute(select(VehicleType)).scalars().one().name == "Citybus 12M"
    assert session.execute(select(Operator)).scalars().one().operator_label == "DPP"


def test_skips_subway(session, patch_get):
    _seed(session, route_type=RouteType.SUBWAY)
    with patch_get([]):
        total = vehicle_descriptors.enrich(session)
    assert total == 0


def test_404_stamps_failure(session, patch_get):
    _seed(session)
    with patch_get(FakeResponse(404)):
        vehicle_descriptors.enrich(session)
    run = session.execute(select(TripRun)).scalars().one()
    assert run.vehicle_id is None
    assert run.additional_data_failed_at is not None


def test_missing_vehicle_descriptor_stamps_failure(session, patch_get):
    _seed(session)
    with patch_get(FakeResponse(200, {"origin_route_name": "100", "vehicle_descriptor": {}})):
        vehicle_descriptors.enrich(session)
    run = session.execute(select(TripRun)).scalars().one()
    assert run.vehicle_id is None
    assert run.additional_data_failed_at is not None
    assert session.execute(select(Vehicle)).scalars().all() == []


def test_same_reg_different_descriptor_creates_new_vehicle(session, patch_get):
    """Reg numbers can be re-used after decommissioning. If any descriptor field
    differs from a prior row with the same reg, insert a new Vehicle."""
    _seed(session)
    with patch_get(FakeResponse(200, VD_PAYLOAD)):
        vehicle_descriptors.enrich(session)
    first_id = session.execute(select(TripRun)).scalars().one().vehicle_id

    # Same trip on a later day, same reg number but USB charger flag flipped.
    later = START_DATE + datetime.timedelta(days=1)
    session.add(TripRun(trip_id="T1", start_date=later, feed_vehicle_id="VEH-2"))
    session.flush()
    ast = ActualStopTime(trip_id="T1", start_date=later, stop_sequence=1, stop_id="S1")
    session.add(ast)
    session.flush()
    ast.updated_at = datetime.datetime.now(datetime.timezone.utc)
    session.commit()

    changed = {
        **VD_PAYLOAD,
        "vehicle_descriptor": {**VD_PAYLOAD["vehicle_descriptor"], "has_usb_chargers": True},
    }
    with patch_get(FakeResponse(200, changed)):
        vehicle_descriptors.enrich(session)

    vehicles = session.execute(select(Vehicle).order_by(Vehicle.vehicle_id)).scalars().all()
    assert len(vehicles) == 2
    assert all(v.registration_number == "REG-001" for v in vehicles)
    assert {v.usb_chargers for v in vehicles} == {False, True}
    second_id = session.execute(select(TripRun).where(TripRun.start_date == later)).scalars().one().vehicle_id
    assert second_id != first_id


def test_cache_hit_skips_api(session, patch_get):
    """When a non-expired Vehicle exists for the feed_vehicle_id, reuse it without calling API."""
    now = datetime.datetime.now(datetime.timezone.utc)
    _seed(session, feed_vehicle_id="service-3-REG-001")
    vt = VehicleType(name="Citybus 12M")
    session.add(vt)
    session.flush()
    v = Vehicle(
        registration_number="REG-001",
        feed_vehicle_id="service-3-REG-001",
        vehicle_type_id=vt.vehicle_type_id,
        last_seen_at=now - datetime.timedelta(hours=1),
        cache_expires_at=now + datetime.timedelta(days=3),
    )
    session.add(v)
    session.commit()

    with patch_get([]) as m:
        vehicle_descriptors.enrich(session)

    assert m.call_count == 0
    run = session.execute(select(TripRun)).scalars().one()
    assert run.vehicle_id == v.vehicle_id
    session.refresh(v)
    assert v.last_seen_at.replace(tzinfo=None) > (now - datetime.timedelta(seconds=5)).replace(tzinfo=None)


def test_cache_miss_when_expired(session, patch_get):
    """Expired cache entry falls through to the API."""
    now = datetime.datetime.now(datetime.timezone.utc)
    _seed(session, feed_vehicle_id="service-3-REG-001")
    vt = VehicleType(name="Citybus 12M")
    session.add(vt)
    session.flush()
    session.add(Vehicle(
        registration_number="REG-001",
        feed_vehicle_id="service-3-REG-001",
        vehicle_type_id=vt.vehicle_type_id,
        last_seen_at=now - datetime.timedelta(days=10),
        cache_expires_at=now - datetime.timedelta(days=1),
    ))
    session.commit()

    with patch_get(FakeResponse(200, VD_PAYLOAD)):
        vehicle_descriptors.enrich(session)

    run = session.execute(select(TripRun)).scalars().one()
    assert run.vehicle_id is not None


def test_cache_miss_different_type_same_reg(session, patch_get):
    """service-0-1234 and service-3-1234 have different types — no cross-type cache hit."""
    now = datetime.datetime.now(datetime.timezone.utc)
    _seed(session, feed_vehicle_id="service-3-1234")
    vt = VehicleType(name="Tram 15T")
    session.add(vt)
    session.flush()
    # Vehicle exists but under a different type code
    session.add(Vehicle(
        registration_number="1234",
        feed_vehicle_id="service-0-1234",
        vehicle_type_id=vt.vehicle_type_id,
        last_seen_at=now,
        cache_expires_at=now + datetime.timedelta(days=3),
    ))
    session.commit()

    with patch_get(FakeResponse(200, VD_PAYLOAD)) as m:
        vehicle_descriptors.enrich(session)

    assert m.call_count == 1


def test_cache_hit_does_not_create_duplicate_vehicle(session, patch_get):
    """Cache hit must not insert a new Vehicle row."""
    now = datetime.datetime.now(datetime.timezone.utc)
    _seed(session, feed_vehicle_id="service-3-REG-001")
    vt = VehicleType(name="Citybus 12M")
    session.add(vt)
    session.flush()
    session.add(Vehicle(
        registration_number="REG-001",
        feed_vehicle_id="service-3-REG-001",
        vehicle_type_id=vt.vehicle_type_id,
        last_seen_at=now,
        cache_expires_at=now + datetime.timedelta(days=3),
    ))
    session.commit()

    with patch_get([]):
        vehicle_descriptors.enrich(session)

    assert len(session.execute(select(Vehicle)).scalars().all()) == 1


def test_second_cycle_hits_cache(session, patch_get):
    """After a successful enrich, the next cycle for the same feed_vehicle_id is a cache hit."""
    _seed(session, feed_vehicle_id="service-3-REG-001")

    # First cycle: cold, hits API
    with patch_get(FakeResponse(200, VD_PAYLOAD)) as m:
        vehicle_descriptors.enrich(session)
    assert m.call_count == 1

    # Simulate a new TripRun for the same vehicle on a later date
    later = START_DATE + datetime.timedelta(days=1)
    session.add(TripRun(trip_id="T1", start_date=later, feed_vehicle_id="service-3-REG-001"))
    session.flush()
    ast = ActualStopTime(trip_id="T1", start_date=later, stop_sequence=1, stop_id="S1")
    session.add(ast)
    session.flush()
    ast.updated_at = datetime.datetime.now(datetime.timezone.utc)
    session.commit()

    # Second cycle: warm, must not call API
    with patch_get([]) as m:
        vehicle_descriptors.enrich(session)
    assert m.call_count == 0
    run = session.execute(select(TripRun).where(TripRun.start_date == later)).scalars().one()
    assert run.vehicle_id is not None


def test_cache_expiry_is_randomized(session):
    """_new_expiry samples uniformly from [TTL_MIN, TTL_MAX]."""
    now = datetime.datetime.now(datetime.timezone.utc)
    expiries = [vehicle_descriptors._new_expiry(now) for _ in range(200)]
    deltas = [(e - now).total_seconds() for e in expiries]
    assert all(vehicle_descriptors.CACHE_TTL_MIN.total_seconds() <= d <= vehicle_descriptors.CACHE_TTL_MAX.total_seconds() for d in deltas)
    assert len(set(deltas)) > 1


def test_transient_requeues_then_gives_up(session, patch_get):
    _seed(session)
    responses = [FakeResponse(500) for _ in range(vehicle_descriptors.MAX_REQUEUES)]
    with patch_get(responses) as m:
        vehicle_descriptors.enrich(session)
    assert m.call_count == vehicle_descriptors.MAX_REQUEUES
    run = session.execute(select(TripRun)).scalars().one()
    assert run.vehicle_id is None
    assert run.additional_data_failed_at is not None
