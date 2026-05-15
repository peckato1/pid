"""trip_runs: add optional p_trip_id filter

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TRIP_RUNS_BODY = """
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
"""


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_runs(DATE, TEXT, INT, INT)")
    op.execute(f"""
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
        LANGUAGE sql STABLE AS $${_TRIP_RUNS_BODY}$$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_runs(DATE, TEXT, TEXT, INT, INT)")
    op.execute("""
        CREATE FUNCTION trip_runs(
            p_date         DATE,
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
            WHERE rtr.start_date = p_date
              AND (p_origin     IS NULL OR rtr.origin_route_name = p_origin)
              AND (p_run        IS NULL OR rtr.run_number        = p_run)
              AND (p_vehicle_id IS NULL OR rtr.vehicle_id        = p_vehicle_id)
            ORDER BY first_st.departure_time;
        $$;
    """)
