"""trip_run_info: expose rt_operator_id

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_run_info(DATE, TEXT)")
    op.execute("""
        CREATE FUNCTION trip_run_info(p_date DATE, p_trip_id TEXT)
        RETURNS TABLE (
            schedule_relationship   TEXT,
            origin_route_name       TEXT,
            run_number              INT,
            updated_at              TIMESTAMPTZ,
            feed_vehicle_id         TEXT,
            vehicle_id              INT,
            registration_number     TEXT,
            vehicle_type            TEXT,
            wheelchair_accessible   BOOLEAN,
            air_conditioned         BOOLEAN,
            usb_chargers            BOOLEAN,
            rt_operator_id          INT,
            rt_operator_label       TEXT,
            rt_agency_id            INT,
            planned_agency_id       INT,
            planned_agency_name     TEXT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                rtr.schedule_relationship::text,
                rtr.origin_route_name,
                rtr.run_number,
                rtr.updated_at,
                rtr.feed_vehicle_id,
                v.vehicle_id,
                v.registration_number,
                vt.name                 AS vehicle_type,
                v.wheelchair_accessible,
                v.air_conditioned,
                v.usb_chargers,
                op.rt_operator_id,
                op.operator_label       AS rt_operator_label,
                op.agency_id            AS rt_agency_id,
                t.agency_id             AS planned_agency_id,
                a.agency_name           AS planned_agency_name
            FROM gtfs_trip t
            LEFT JOIN gtfs_agency a
                   ON a.agency_id = t.agency_id
                  AND a.valid_from <= p_date
                  AND (a.valid_until IS NULL OR a.valid_until > p_date)
            LEFT JOIN rt_trip rtr
                   ON rtr.trip_id = t.trip_id
                  AND rtr.start_date = p_date
            LEFT JOIN rt_vehicle v        ON v.vehicle_id = rtr.vehicle_id
            LEFT JOIN rt_vehicle_type vt  ON vt.vehicle_type_id = v.vehicle_type_id
            LEFT JOIN rt_operator op      ON op.rt_operator_id = v.operator_id
            WHERE t.trip_id = p_trip_id
              AND t.valid_from <= p_date
              AND (t.valid_until IS NULL OR t.valid_until > p_date);
        $$;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_run_info(DATE, TEXT)")
    op.execute("""
        CREATE FUNCTION trip_run_info(p_date DATE, p_trip_id TEXT)
        RETURNS TABLE (
            schedule_relationship   TEXT,
            origin_route_name       TEXT,
            run_number              INT,
            updated_at              TIMESTAMPTZ,
            feed_vehicle_id         TEXT,
            vehicle_id              INT,
            registration_number     TEXT,
            vehicle_type            TEXT,
            wheelchair_accessible   BOOLEAN,
            air_conditioned         BOOLEAN,
            usb_chargers            BOOLEAN,
            rt_operator_label       TEXT,
            rt_agency_id            INT,
            planned_agency_id       INT,
            planned_agency_name     TEXT
        )
        LANGUAGE sql STABLE AS $$
            SELECT
                rtr.schedule_relationship::text,
                rtr.origin_route_name,
                rtr.run_number,
                rtr.updated_at,
                rtr.feed_vehicle_id,
                v.vehicle_id,
                v.registration_number,
                vt.name                 AS vehicle_type,
                v.wheelchair_accessible,
                v.air_conditioned,
                v.usb_chargers,
                op.operator_label       AS rt_operator_label,
                op.agency_id            AS rt_agency_id,
                t.agency_id             AS planned_agency_id,
                a.agency_name           AS planned_agency_name
            FROM gtfs_trip t
            LEFT JOIN gtfs_agency a
                   ON a.agency_id = t.agency_id
                  AND a.valid_from <= p_date
                  AND (a.valid_until IS NULL OR a.valid_until > p_date)
            LEFT JOIN rt_trip rtr
                   ON rtr.trip_id = t.trip_id
                  AND rtr.start_date = p_date
            LEFT JOIN rt_vehicle v        ON v.vehicle_id = rtr.vehicle_id
            LEFT JOIN rt_vehicle_type vt  ON vt.vehicle_type_id = v.vehicle_type_id
            LEFT JOIN rt_operator op      ON op.rt_operator_id = v.operator_id
            WHERE t.trip_id = p_trip_id
              AND t.valid_from <= p_date
              AND (t.valid_until IS NULL OR t.valid_until > p_date);
        $$;
    """)
