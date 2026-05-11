import collections
import datetime
import logging

import requests
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from pid import golemio
from pid.models.enums import RouteType
from pid.models.realtime import ActualStopTime, Operator, TripRun, Vehicle, VehicleType
from pid.models.route import Route
from pid.models.trip import Trip

logger = logging.getLogger(__name__)

SERVICE_PATH = "/v2/public/vehiclepositions/{vehicle_id};gtfsTripId={trip_id}?scopes[]=info&scopes[]=vehicle_descriptor"
# A trip is considered "live" if it has produced a stop-time update in this window;
# only live trips are queryable on the per-service endpoint.
ACTIVE_WINDOW = datetime.timedelta(minutes=5)
# How long before retrying a previously-failed enrichment. Avoids hammering 404s
# for trips the per-service endpoint never returns (not yet started or already over).
RETRY_BACKOFF = datetime.timedelta(minutes=3)
# Max attempts per candidate within a single cycle for transient outcomes.
MAX_REQUEUES = 5
# Outcomes treated as transient (worth requeueing) vs. terminal (4xx, no descriptor).
TRANSIENT_STATUSES = {0, 429, 500, 502, 503, 504}
# Route types the per-service endpoint never returns descriptor data for — skip
# them entirely instead of paying for guaranteed 404 / no_vehicle_descriptor responses.
SKIP_ROUTE_TYPES = (RouteType.RAIL, RouteType.SUBWAY)


def _fetch_service(feed_vehicle_id: str, trip_id: str) -> tuple[int, dict | None]:
    # Single attempt per call; the caller decides whether to requeue on transient
    # failures. golemio.get() handles the rate-limit sleep so the next call
    # (whichever candidate that is) starts fresh.
    path = SERVICE_PATH.format(vehicle_id=feed_vehicle_id, trip_id=trip_id)
    try:
        r = golemio.get(path)
    except requests.RequestException as exc:
        logger.debug("network error (%s) for trip=%s", exc.__class__.__name__, trip_id)
        return 0, None
    if r.status_code != 200:
        return r.status_code, None
    return 200, r.json()


def _get_or_create_vehicle_type(session: Session, name: str | None) -> int | None:
    if not name:
        return None
    vt = session.execute(
        select(VehicleType).where(VehicleType.name == name)
    ).scalar_one_or_none()
    if vt is None:
        vt = VehicleType(name=name)
        session.add(vt)
        session.flush()
    return vt.vehicle_type_id


def _get_or_create_operator(session: Session, operator_label: str | None) -> int | None:
    if not operator_label:
        return None
    a = session.execute(
        select(Operator).where(Operator.operator_label == operator_label)
    ).scalar_one_or_none()
    if a is None:
        a = Operator(operator_label=operator_label, agency_id=None)
        session.add(a)
        session.flush()
    return a.rt_operator_id


def _upsert_vehicle(session: Session, vd_data: dict, type_id: int | None, operator_id: int | None) -> int | None:
    # Reg numbers can be re-used after a vehicle is decommissioned, so they're
    # not a unique key. We treat (reg_number + all descriptor fields) as the
    # identity: if every field matches, reuse the row; otherwise insert a new
    # one to preserve the history.
    label = vd_data.get("vehicle_registration_number") or None
    if label is None:
        return None
    fields = dict(
        vehicle_type_id=type_id,
        operator_id=operator_id,
        wheelchair_accessible=vd_data.get("is_wheelchair_accessible"),
        air_conditioned=vd_data.get("is_air_conditioned"),
        usb_chargers=vd_data.get("has_usb_chargers"),
    )
    vehicle = session.execute(
        select(Vehicle)
        .where(Vehicle.registration_number == label)
        .where(*[getattr(Vehicle, k).is_(v) if v is None else getattr(Vehicle, k) == v for k, v in fields.items()])
    ).scalars().first()
    if vehicle is None:
        vehicle = Vehicle(registration_number=label, **fields)
        session.add(vehicle)
        session.flush()
        logger.info("new vehicle reg=%s vehicle_id=%s type=%s operator=%s", label, vehicle.vehicle_id, vd_data.get("vehicle_type"), vd_data.get("operator"))
    return vehicle.vehicle_id


def enrich(session: Session, limit: int | None = None) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - ACTIVE_WINDOW
    retry_cutoff = now - RETRY_BACKOFF
    # A trip is a candidate iff:
    #   - it doesn't already have descriptor data (vehicle_id IS NULL)
    #   - we have a feed_vehicle_id to query the per-service endpoint with
    #   - it's currently live (recent ActualStopTime update)
    #   - its route_type isn't in SKIP_ROUTE_TYPES (those never resolve)
    #   - we haven't recently failed to enrich it (RETRY_BACKOFF)
    active = (
        select(ActualStopTime.trip_id)
        .where(ActualStopTime.trip_id == TripRun.trip_id)
        .where(ActualStopTime.start_date == TripRun.start_date)
        .where(ActualStopTime.updated_at > cutoff)
    )
    skip_route = (
        select(Trip.trip_id)
        .join(Route, Route.route_id == Trip.route_id)
        .where(Trip.trip_id == TripRun.trip_id)
        .where(Route.route_type.in_(SKIP_ROUTE_TYPES))
    )
    stmt = (
        select(TripRun)
        .where(TripRun.vehicle_id.is_(None))
        .where(TripRun.feed_vehicle_id.is_not(None))
        .where(active.exists())
        .where(~skip_route.exists())
        .where(or_(
            TripRun.additional_data_failed_at.is_(None),
            TripRun.additional_data_failed_at < retry_cutoff,
        ))
        .order_by(TripRun.updated_at.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    candidates = session.execute(stmt).scalars().all()
    total = len(candidates)
    logger.info("cycle start: %d candidate(s)", total)

    # Deque so transient failures can be pushed to the back and retried later in
    # the same cycle while we make progress on other candidates.
    queue: collections.deque = collections.deque((tr, 0) for tr in candidates)
    enriched = 0
    failures: collections.Counter = collections.Counter()
    processed = 0
    while queue:
        tr, attempts = queue.popleft()
        processed += 1
        status, data = _fetch_service(tr.feed_vehicle_id, tr.trip_id)

        # Transient: requeue up to MAX_REQUEUES, then give up and stamp the failure.
        # Terminal (else branches): stamp immediately.
        if status in TRANSIENT_STATUSES:
            if attempts + 1 < MAX_REQUEUES:
                queue.append((tr, attempts + 1))
                logger.debug("[%d] trip=%s feed_vehicle=%s status=%s -> requeue (attempt %d/%d)", processed, tr.trip_id, tr.feed_vehicle_id, status, attempts + 1, MAX_REQUEUES)
                continue
            failures[f"transient_{status}"] += 1
            tr.additional_data_failed_at = datetime.datetime.now(datetime.timezone.utc)
            logger.warning("[%d] trip=%s feed_vehicle=%s status=%s -> giving up after %d attempts", processed, tr.trip_id, tr.feed_vehicle_id, status, attempts + 1)
        elif data is None:
            failures[status] += 1
            tr.additional_data_failed_at = datetime.datetime.now(datetime.timezone.utc)
            logger.debug("[%d] trip=%s feed_vehicle=%s status=%s -> no data", processed, tr.trip_id, tr.feed_vehicle_id, status)
        else:
            vd_data = data.get("vehicle_descriptor") or {}
            if not vd_data.get("vehicle_registration_number"):
                failures["no_vehicle_descriptor"] += 1
                tr.additional_data_failed_at = datetime.datetime.now(datetime.timezone.utc)
                logger.debug("[%d] trip=%s feed_vehicle=%s -> no vehicle_descriptor", processed, tr.trip_id, tr.feed_vehicle_id)
            else:
                type_id = _get_or_create_vehicle_type(session, vd_data.get("vehicle_type"))
                operator_id = _get_or_create_operator(session, vd_data.get("operator"))
                vehicle_id = _upsert_vehicle(session, vd_data, type_id, operator_id)
                tr.vehicle_id = vehicle_id
                tr.origin_route_name = data.get("origin_route_name")
                tr.run_number = data.get("run_number")
                enriched += 1
                logger.debug("[%d] trip=%s feed_vehicle=%s -> vehicle=%s reg=%s", processed, tr.trip_id, tr.feed_vehicle_id, vehicle_id, vd_data.get("vehicle_registration_number"))

        # Commit per row to keep row-level locks short — the ingest writer also
        # updates rt_trip and we'd deadlock under batched commits.
        try:
            session.commit()
        except Exception as exc:
            logger.error("commit failed for trip=%s: %s", tr.trip_id, exc)
            session.rollback()
            failures["commit_error"] += 1

    logger.info("cycle done: enriched %d/%d; failures=%s", enriched, total, dict(failures))
    return total


