import datetime
import logging
import time

from pid.proto import gtfs_realtime_OVapi_pb2, gtfs_realtime_pb2
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from pid import golemio
from pid.models.enums import ScheduleRelationship
from pid.models.realtime import ActualStopTime, TripRun

# We persist *actual* (already-served) stop times only — future predictions
# are volatile and would just be overwritten on the next sync. To do that we
# need the vehicle's current stop_sequence per trip, which lives in a separate
# VehiclePosition entity in the same feed; we resolve it up front and then
# truncate each TripUpdate's stop_time_update list to seqs <= max_seq.

logger = logging.getLogger(__name__)

FEED_PATH = "/v2/vehiclepositions/gtfsrt/pid_feed.pb"

STOPPED_AT = 1


def _build_vehicle_positions(feed) -> dict[str, int]:
    """Map trip_id -> max stop_sequence the vehicle has reached (inclusive)."""
    positions = {}
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vp = entity.vehicle
        trip_id = vp.trip.trip_id
        if not trip_id:
            continue
        seq = vp.current_stop_sequence
        # STOPPED_AT: vehicle is at this stop, so include it.
        # INCOMING_AT / IN_TRANSIT_TO: vehicle hasn't served this stop yet.
        if vp.current_status != STOPPED_AT:
            seq -= 1
        positions[trip_id] = seq
    return positions


def sync(session: Session, routes: set[str] | None = None, dry_run: bool = False) -> None:
    t0 = time.monotonic()
    r = golemio.get(FEED_PATH)
    r.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(r.content)
    fetch_secs = time.monotonic() - t0
    logger.debug("fetched %d bytes in %.2fs (entities=%d)", len(r.content), fetch_secs, len(feed.entity))

    now = datetime.datetime.now(datetime.timezone.utc)
    vehicle_positions = _build_vehicle_positions(feed)

    counts = {
        "entities": len(feed.entity),
        "trip_updates": 0,
        "skipped_route_filter": 0,
        "skipped_no_start_date": 0,
        "skipped_no_position": 0,
        "trip_runs_written": 0,
        "trip_runs_with_vehicle": 0,
        "stop_times_written": 0,
        "errors": 0,
    }
    error_samples: list[str] = []

    trip_run_rows: list[dict] = []
    stop_time_rows: list[dict] = []

    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        counts["trip_updates"] += 1

        tu = entity.trip_update
        trip = tu.trip

        if routes and trip.route_id not in routes:
            counts["skipped_route_filter"] += 1
            logger.debug("skip trip_id=%s reason=route_filter route=%s", trip.trip_id, trip.route_id)
            continue

        if not trip.start_date:
            counts["skipped_no_start_date"] += 1
            logger.debug("skip trip_id=%s reason=no_start_date", trip.trip_id)
            continue

        try:
            start_date = datetime.datetime.strptime(trip.start_date, "%Y%m%d").date()

            # No VehiclePosition for this trip means we don't know how far it
            # has progressed, so we can't tell which stop_time_updates are
            # actual vs predicted. Skip the whole trip rather than guess.
            max_seq = vehicle_positions.get(trip.trip_id)
            if max_seq is None:
                counts["skipped_no_position"] += 1
                logger.debug("skip trip_id=%s reason=no_position", trip.trip_id)
                continue

            feed_vehicle_id = tu.vehicle.id if tu.HasField("vehicle") else None

            if dry_run:
                logger.info("TripRun trip_id=%s route_id=%s start_date=%s feed_vehicle_id=%s schedule_relationship=%s", trip.trip_id, trip.route_id, start_date, feed_vehicle_id, trip.schedule_relationship)
            else:
                trip_run_rows.append({
                    "trip_id": trip.trip_id,
                    "start_date": start_date,
                    "feed_vehicle_id": feed_vehicle_id,
                    "schedule_relationship": ScheduleRelationship(trip.schedule_relationship),
                    "updated_at": now,
                })
            counts["trip_runs_written"] += 1
            if feed_vehicle_id:
                counts["trip_runs_with_vehicle"] += 1

            stop_times_for_trip = 0
            # stop_time_update is ordered by stop_sequence in the GTFS-RT feed,
            # so once we pass max_seq everything remaining is a future prediction.
            for stu in tu.stop_time_update:
                if stu.stop_sequence > max_seq:
                    break
                ovapi_stu = stu.Extensions[gtfs_realtime_OVapi_pb2.ovapi_stop_time_update]
                arr = stu.arrival.delay if stu.HasField("arrival") else None
                dep = stu.departure.delay if stu.HasField("departure") else None
                track_sched = ovapi_stu.scheduled_track or None
                track_act = ovapi_stu.actual_track or None
                headsign = ovapi_stu.stop_headsign or None
                if dry_run:
                    logger.info("  ActualStopTime seq=%s stop_id=%s arr_delay=%s dep_delay=%s track=%s->%s headsign=%s", stu.stop_sequence, stu.stop_id, arr, dep, track_sched, track_act, headsign)
                else:
                    stop_time_rows.append({
                        "trip_id": trip.trip_id,
                        "start_date": start_date,
                        "stop_sequence": stu.stop_sequence,
                        "stop_id": stu.stop_id,
                        "arrival_delay": arr,
                        "departure_delay": dep,
                        "track_scheduled": track_sched,
                        "track_actual": track_act,
                        "headsign": headsign,
                        "updated_at": now,
                    })
                counts["stop_times_written"] += 1
                stop_times_for_trip += 1
            logger.debug("trip_id=%s wrote %d stop_times (max_seq=%d)", trip.trip_id, stop_times_for_trip, max_seq)
        except Exception as e:
            counts["errors"] += 1
            if len(error_samples) < 5:
                error_samples.append(f"trip_id={trip.trip_id}: {type(e).__name__}: {e}")
            logger.debug("error processing trip_id=%s", trip.trip_id, exc_info=True)

    if not dry_run:
        commit_t0 = time.monotonic()
        # Postgres caps bind parameters at 65535 per statement (16-bit field in
        # the wire protocol), so chunk so rows_per_chunk * cols stays under.
        def _chunks(rows, cols, limit=50000):
            size = max(1, limit // cols)
            for i in range(0, len(rows), size):
                yield rows[i:i + size]

        for chunk in _chunks(trip_run_rows, 5):
            stmt = pg_insert(TripRun).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trip_id", "start_date"],
                set_={
                    "feed_vehicle_id": stmt.excluded.feed_vehicle_id,
                    "schedule_relationship": stmt.excluded.schedule_relationship,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)
        for chunk in _chunks(stop_time_rows, 10):
            stmt = pg_insert(ActualStopTime).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trip_id", "start_date", "stop_sequence"],
                set_={
                    "stop_id": stmt.excluded.stop_id,
                    "arrival_delay": stmt.excluded.arrival_delay,
                    "departure_delay": stmt.excluded.departure_delay,
                    "track_scheduled": stmt.excluded.track_scheduled,
                    "track_actual": stmt.excluded.track_actual,
                    "headsign": stmt.excluded.headsign,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)
        session.commit()
        commit_secs = time.monotonic() - commit_t0
    else:
        commit_secs = 0.0

    total_secs = time.monotonic() - t0
    logger.info(
        "sync done in %.2fs (fetch %.2fs, commit %.2fs); "
        "entities=%s trip_updates=%s "
        "trip_runs=%s (with vehicle: %s) "
        "stop_times=%s "
        "skipped(route=%s, no_date=%s, no_position=%s) "
        "errors=%s",
        total_secs, fetch_secs, commit_secs,
        counts['entities'], counts['trip_updates'],
        counts['trip_runs_written'], counts['trip_runs_with_vehicle'],
        counts['stop_times_written'],
        counts['skipped_route_filter'], counts['skipped_no_start_date'], counts['skipped_no_position'],
        counts['errors'],
    )
    for sample in error_samples:
        logger.warning("  error: %s", sample)
