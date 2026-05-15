"""trip_runs, trip_schedule: expose stop_id columns; drop trip_schedule_at

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-15 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_schedule_at(date, text, text)")

    op.execute("DROP FUNCTION IF EXISTS trip_schedule(DATE, TEXT)")
    op.execute("""
        CREATE FUNCTION trip_schedule(p_date DATE, p_trip_id TEXT)
        RETURNS TABLE (
            stop_sequence       SMALLINT,
            stop_id             TEXT,
            stop_name           TEXT,
            planned_platform    TEXT,
            track_scheduled     TEXT,
            track_actual        TEXT,
            planned_arrival     TEXT,
            planned_departure   TEXT,
            arrival_delay       INT,
            departure_delay     INT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                st.stop_sequence,
                COALESCE(parent.stop_id, s.stop_id)         AS stop_id,
                COALESCE(parent.stop_name, s.stop_name)     AS stop_name,
                s.platform_code                             AS planned_platform,
                rt.track_scheduled,
                rt.track_actual,
                st.arrival_time                             AS planned_arrival,
                st.departure_time                           AS planned_departure,
                rt.arrival_delay,
                rt.departure_delay
            FROM gtfs_stop_times st
            JOIN gtfs_stop s
                   ON s.stop_id = st.stop_id
                  AND s.valid_from <= p_date
                  AND (s.valid_until IS NULL OR s.valid_until > p_date)
            LEFT JOIN gtfs_stop parent
                   ON parent.stop_id = s.parent_station_id
                  AND parent.valid_from <= p_date
                  AND (parent.valid_until IS NULL OR parent.valid_until > p_date)
            LEFT JOIN rt_stop_time rt
                   ON rt.trip_id       = st.trip_id
                  AND rt.stop_sequence = st.stop_sequence
                  AND rt.start_date    = p_date
            WHERE st.trip_id = p_trip_id
              AND st.valid_from <= p_date
              AND (st.valid_until IS NULL OR st.valid_until > p_date)
            ORDER BY st.stop_sequence;
        $$;
    """)

    op.execute("DROP FUNCTION IF EXISTS trip_runs(DATE, TEXT, TEXT, INT, INT)")
    op.execute("""
        CREATE FUNCTION trip_runs(
            p_date         DATE DEFAULT NULL,
            p_trip_id      TEXT DEFAULT NULL,
            p_origin       TEXT DEFAULT NULL,
            p_run          INT  DEFAULT NULL,
            p_vehicle_id   INT  DEFAULT NULL
        )
        RETURNS TABLE (
            trip_id                TEXT,
            start_date             DATE,
            vehicle_id             INT,
            registration_number    TEXT,
            operator_id            INT,
            operator_label         TEXT,
            origin_route_name      TEXT,
            run_number             INT,
            start_stop_id          TEXT,
            start_stop             TEXT,
            start_time             TEXT,
            end_stop_id            TEXT,
            end_stop               TEXT,
            end_time               TEXT,
            schedule_relationship  TEXT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                rtr.trip_id,
                rtr.start_date,
                rtr.vehicle_id,
                v.registration_number,
                op.rt_operator_id        AS operator_id,
                op.operator_label,
                rtr.origin_route_name,
                rtr.run_number,
                first_stop.stop_id       AS start_stop_id,
                first_stop.stop_name     AS start_stop,
                first_st.departure_time  AS start_time,
                last_stop.stop_id        AS end_stop_id,
                last_stop.stop_name      AS end_stop,
                last_st.arrival_time     AS end_time,
                rtr.schedule_relationship::text
            FROM rt_trip rtr
            LEFT JOIN rt_vehicle  v  ON v.vehicle_id      = rtr.vehicle_id
            LEFT JOIN rt_operator op ON op.rt_operator_id = v.operator_id
            LEFT JOIN LATERAL (
                SELECT * FROM gtfs_stop_times st
                WHERE st.trip_id = rtr.trip_id
                  AND st.valid_from <= rtr.start_date
                  AND (st.valid_until IS NULL OR st.valid_until > rtr.start_date)
                ORDER BY st.stop_sequence ASC LIMIT 1
            ) first_st ON TRUE
            LEFT JOIN LATERAL (
                SELECT * FROM gtfs_stop_times st
                WHERE st.trip_id = rtr.trip_id
                  AND st.valid_from <= rtr.start_date
                  AND (st.valid_until IS NULL OR st.valid_until > rtr.start_date)
                ORDER BY st.stop_sequence DESC LIMIT 1
            ) last_st ON TRUE
            LEFT JOIN gtfs_stop first_stop
                   ON first_stop.stop_id = first_st.stop_id
                  AND first_stop.valid_from <= rtr.start_date
                  AND (first_stop.valid_until IS NULL OR first_stop.valid_until > rtr.start_date)
            LEFT JOIN gtfs_stop last_stop
                   ON last_stop.stop_id = last_st.stop_id
                  AND last_stop.valid_from <= rtr.start_date
                  AND (last_stop.valid_until IS NULL OR last_stop.valid_until > rtr.start_date)
            WHERE (p_date        IS NULL OR rtr.start_date         = p_date)
              AND (p_trip_id     IS NULL OR rtr.trip_id            = p_trip_id)
              AND (p_origin      IS NULL OR rtr.origin_route_name  = p_origin)
              AND (p_run         IS NULL OR rtr.run_number         = p_run)
              AND (p_vehicle_id  IS NULL OR rtr.vehicle_id         = p_vehicle_id)
            ORDER BY rtr.start_date DESC, first_st.departure_time;
        $$;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE FUNCTION trip_schedule_at(as_of date, query_route_short_name text DEFAULT NULL, query_trip_id text DEFAULT NULL)
        RETURNS TABLE (
            trip_id          text,
            route_short_name text,
            route_type       text,
            trip_headsign    text,
            direction_id     text,
            service_id       text,
            stop_sequence    int,
            arrival_time     text,
            departure_time   text,
            stop_headsign    text,
            pickup_type      text,
            drop_off_type    text,
            stop_id          text,
            stop_name        text,
            stop_platform    text,
            stop_farezone    text,
            stop_region      text
        ) LANGUAGE sql STABLE AS $$
            SELECT
                t.trip_id,
                r.route_short_name,
                r.route_type::text,
                t.trip_headsign,
                t.direction_id::text,
                t.service_id,
                st.stop_sequence::int,
                st.arrival_time,
                st.departure_time,
                st.stop_headsign,
                st.pickup_type::text,
                st.drop_off_type::text,
                s.stop_id,
                s.stop_name,
                s.platform_code,
                s.zone_id,
                s.zone_region_type::text
            FROM gtfs_trip t
            JOIN gtfs_stop_times st ON st.trip_id = t.trip_id
                AND st.valid_from <= as_of AND (st.valid_until IS NULL OR st.valid_until > as_of)
            JOIN gtfs_route r ON r.route_id = t.route_id
                AND r.valid_from  <= as_of AND (r.valid_until  IS NULL OR r.valid_until  > as_of)
            JOIN gtfs_stop s ON s.stop_id = st.stop_id
                AND s.valid_from  <= as_of AND (s.valid_until  IS NULL OR s.valid_until  > as_of)
            WHERE (query_route_short_name IS NULL OR r.route_short_name = query_route_short_name)
              AND (query_trip_id IS NULL OR t.trip_id = query_trip_id)
              AND t.valid_from <= as_of AND (t.valid_until IS NULL OR t.valid_until > as_of)
            ORDER BY t.trip_id, st.stop_sequence;
        $$
    """)

    op.execute("DROP FUNCTION IF EXISTS trip_schedule(DATE, TEXT)")
    op.execute("""
        CREATE FUNCTION trip_schedule(p_date DATE, p_trip_id TEXT)
        RETURNS TABLE (
            stop_sequence       SMALLINT,
            stop_name           TEXT,
            planned_platform    TEXT,
            track_scheduled     TEXT,
            track_actual        TEXT,
            planned_arrival     TEXT,
            planned_departure   TEXT,
            arrival_delay       INT,
            departure_delay     INT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                st.stop_sequence,
                COALESCE(parent.stop_name, s.stop_name)     AS stop_name,
                s.platform_code                             AS planned_platform,
                rt.track_scheduled,
                rt.track_actual,
                st.arrival_time                             AS planned_arrival,
                st.departure_time                           AS planned_departure,
                rt.arrival_delay,
                rt.departure_delay
            FROM gtfs_stop_times st
            JOIN gtfs_stop s
                   ON s.stop_id = st.stop_id
                  AND s.valid_from <= p_date
                  AND (s.valid_until IS NULL OR s.valid_until > p_date)
            LEFT JOIN gtfs_stop parent
                   ON parent.stop_id = s.parent_station_id
                  AND parent.valid_from <= p_date
                  AND (parent.valid_until IS NULL OR parent.valid_until > p_date)
            LEFT JOIN rt_stop_time rt
                   ON rt.trip_id       = st.trip_id
                  AND rt.stop_sequence = st.stop_sequence
                  AND rt.start_date    = p_date
            WHERE st.trip_id = p_trip_id
              AND st.valid_from <= p_date
              AND (st.valid_until IS NULL OR st.valid_until > p_date)
            ORDER BY st.stop_sequence;
        $$;
    """)

    op.execute("DROP FUNCTION IF EXISTS trip_runs(DATE, TEXT, TEXT, INT, INT)")
    op.execute("""
        CREATE FUNCTION trip_runs(
            p_date         DATE DEFAULT NULL,
            p_trip_id      TEXT DEFAULT NULL,
            p_origin       TEXT DEFAULT NULL,
            p_run          INT  DEFAULT NULL,
            p_vehicle_id   INT  DEFAULT NULL
        )
        RETURNS TABLE (
            trip_id                TEXT,
            start_date             DATE,
            vehicle_id             INT,
            registration_number    TEXT,
            operator_id            INT,
            operator_label         TEXT,
            origin_route_name      TEXT,
            run_number             INT,
            start_stop             TEXT,
            start_time             TEXT,
            end_stop               TEXT,
            end_time               TEXT,
            schedule_relationship  TEXT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                rtr.trip_id,
                rtr.start_date,
                rtr.vehicle_id,
                v.registration_number,
                op.rt_operator_id        AS operator_id,
                op.operator_label,
                rtr.origin_route_name,
                rtr.run_number,
                first_stop.stop_name     AS start_stop,
                first_st.departure_time  AS start_time,
                last_stop.stop_name      AS end_stop,
                last_st.arrival_time     AS end_time,
                rtr.schedule_relationship::text
            FROM rt_trip rtr
            LEFT JOIN rt_vehicle  v  ON v.vehicle_id      = rtr.vehicle_id
            LEFT JOIN rt_operator op ON op.rt_operator_id = v.operator_id
            LEFT JOIN LATERAL (
                SELECT * FROM gtfs_stop_times st
                WHERE st.trip_id = rtr.trip_id
                  AND st.valid_from <= rtr.start_date
                  AND (st.valid_until IS NULL OR st.valid_until > rtr.start_date)
                ORDER BY st.stop_sequence ASC LIMIT 1
            ) first_st ON TRUE
            LEFT JOIN LATERAL (
                SELECT * FROM gtfs_stop_times st
                WHERE st.trip_id = rtr.trip_id
                  AND st.valid_from <= rtr.start_date
                  AND (st.valid_until IS NULL OR st.valid_until > rtr.start_date)
                ORDER BY st.stop_sequence DESC LIMIT 1
            ) last_st ON TRUE
            LEFT JOIN gtfs_stop first_stop
                   ON first_stop.stop_id = first_st.stop_id
                  AND first_stop.valid_from <= rtr.start_date
                  AND (first_stop.valid_until IS NULL OR first_stop.valid_until > rtr.start_date)
            LEFT JOIN gtfs_stop last_stop
                   ON last_stop.stop_id = last_st.stop_id
                  AND last_stop.valid_from <= rtr.start_date
                  AND (last_stop.valid_until IS NULL OR last_stop.valid_until > rtr.start_date)
            WHERE (p_date        IS NULL OR rtr.start_date         = p_date)
              AND (p_trip_id     IS NULL OR rtr.trip_id            = p_trip_id)
              AND (p_origin      IS NULL OR rtr.origin_route_name  = p_origin)
              AND (p_run         IS NULL OR rtr.run_number         = p_run)
              AND (p_vehicle_id  IS NULL OR rtr.vehicle_id         = p_vehicle_id)
            ORDER BY rtr.start_date DESC, first_st.departure_time;
        $$;
    """)
