"""initial schema (gtfs_-prefixed static tables + rt_ realtime tables + functions)

Revision ID: 0001
Revises:
Create Date: 2026-05-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import MetaData
import geoalchemy2


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE transferflags AS ENUM ('Ma', 'Mb', 'Mc', 'Md', 'Ra', 'Sb', 'Fu', 'Fe', 'Ap', 'Tr', 'Tb', 'Bu')")

    op.create_table('gtfs_agency',
        sa.Column('agency_id', sa.Integer(), nullable=False),
        sa.Column('agency_name', sa.String(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('agency_id', 'valid_from'),
    )
    op.create_table('gtfs_calendar',
        sa.Column('service_id', sa.String(), nullable=False),
        sa.Column('monday', sa.Boolean(), nullable=False),
        sa.Column('tuesday', sa.Boolean(), nullable=False),
        sa.Column('wednesday', sa.Boolean(), nullable=False),
        sa.Column('thursday', sa.Boolean(), nullable=False),
        sa.Column('friday', sa.Boolean(), nullable=False),
        sa.Column('saturday', sa.Boolean(), nullable=False),
        sa.Column('sunday', sa.Boolean(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('service_id', 'valid_from'),
    )
    op.create_table('gtfs_calendar_date',
        sa.Column('service_id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('exception_type', sa.Enum('ADDED', 'REMOVED', name='exceptiontype'), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('service_id', 'date', 'valid_from'),
    )
    op.create_table('gtfs_route',
        sa.Column('route_id', sa.String(), nullable=False),
        sa.Column('route_short_name', sa.String(), nullable=True),
        sa.Column('route_long_name', sa.String(), nullable=True),
        sa.Column('route_type', sa.Enum('TRAM', 'SUBWAY', 'RAIL', 'BUS', 'FERRY', 'CABLE_TRAM', 'AERIAL_LIFT', 'FUNICULAR', 'TROLLEYBUS', 'MONORAIL', name='routetype'), nullable=True),
        sa.Column('route_url', sa.String(), nullable=True),
        sa.Column('route_color', sa.String(length=6), nullable=True),
        sa.Column('route_text_color', sa.String(length=6), nullable=True),
        sa.Column('is_night', sa.Boolean(), nullable=True),
        sa.Column('is_regional', sa.Boolean(), nullable=True),
        sa.Column('is_substitute_transport', sa.Boolean(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('route_id', 'valid_from'),
    )
    op.create_table('gtfs_route_agency',
        sa.Column('route_id', sa.String(), nullable=False),
        sa.Column('agency_id', sa.Integer(), nullable=False),
        sa.Column('route_licence_number', sa.Integer(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('route_id', 'agency_id', 'valid_from'),
    )
    op.create_table('gtfs_route_stop',
        sa.Column('route_id', sa.String(), nullable=False),
        sa.Column('direction_id', sa.SmallInteger(), nullable=False),
        sa.Column('stop_sequence', sa.SmallInteger(), nullable=False),
        sa.Column('stop_id', sa.String(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('route_id', 'direction_id', 'stop_sequence', 'valid_from'),
    )
    op.create_table('gtfs_shape',
        sa.Column('shape_id', sa.String(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='LINESTRING', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry', nullable=False), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('shape_id', 'valid_from'),
    )
    op.create_table('gtfs_stop',
        sa.Column('stop_id', sa.String(), nullable=False),
        sa.Column('stop_name', sa.String(), nullable=True),
        sa.Column('geometry', geoalchemy2.types.Geometry(geometry_type='POINT', srid=4326, dimension=2, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column('zone_id', sa.String(), nullable=True),
        sa.Column('stop_url', sa.String(), nullable=True),
        sa.Column('location_type', sa.Enum('STOP', 'STATION', 'ENTRANCE_EXIT', 'GENERIC_NODE', 'BOARDING_AREA', name='stoplocationtype'), nullable=True),
        sa.Column('parent_station_id', sa.String(), nullable=True),
        sa.Column('wheelchair_boarding', sa.Integer(), nullable=True),
        sa.Column('level_id', sa.String(), nullable=True),
        sa.Column('platform_code', sa.String(), nullable=True),
        sa.Column('asw_node_id', sa.Integer(), nullable=True),
        sa.Column('asw_stop_id', sa.Integer(), nullable=True),
        sa.Column('zone_region_type', sa.Enum('AUXILIARY', 'PRAGUE', 'CENTRAL_BOHEMIA', 'PID_FULL', 'PID_TRANSIT', 'PID_NONE', name='zoneregiontype'), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('stop_id', 'valid_from'),
    )
    op.create_table('gtfs_stop_times',
        sa.Column('trip_id', sa.String(), nullable=False),
        sa.Column('stop_id', sa.String(), nullable=False),
        sa.Column('stop_sequence', sa.SmallInteger(), nullable=False),
        sa.Column('arrival_time', sa.String(length=8), nullable=True),
        sa.Column('departure_time', sa.String(length=8), nullable=True),
        sa.Column('stop_headsign', sa.String(), nullable=True),
        sa.Column('pickup_type', sa.Enum('REGULAR', 'NO_PICKUP', 'MUST_PHONE', 'MUST_COORDINATE_WITH_DRIVER', name='pickuptype'), server_default='REGULAR', nullable=False),
        sa.Column('drop_off_type', sa.Enum('REGULAR', 'NO_DROP_OFF', 'MUST_PHONE', 'MUST_COORDINATE_WITH_DRIVER', name='dropofftype'), server_default='REGULAR', nullable=False),
        sa.Column('shape_dist_traveled', sa.Float(), nullable=True),
        sa.Column('trip_operation_type', sa.Enum('REGULAR', 'FROM_DEPOT', 'TO_DEPOT', 'LINE_TRANSFER_SAME_LINE', 'LINE_TRANSFER_OTHER_LINE', name='tripoperationtype'), nullable=True),
        sa.Column('bikes_allowed', sa.Enum('UNKNOWN', 'ALLOWED', 'NOT_ALLOWED', 'ALLOWED_NO_ENTRY_EXIT', 'ALLOWED_NO_ENTRY', 'ALLOWED_NO_EXIT', name='bikesallowed'), nullable=True),
        sa.Column('stop_icons', sa.ARRAY(sa.Enum('Ma', 'Mb', 'Mc', 'Md', 'Ra', 'Sb', 'Fu', 'Fe', 'Ap', 'Tr', 'Tb', 'Bu', name='transferflags', metadata=MetaData())), nullable=True),
        sa.Column('headsign_icons', sa.ARRAY(sa.Enum('Ma', 'Mb', 'Mc', 'Md', 'Ra', 'Sb', 'Fu', 'Fe', 'Ap', 'Tr', 'Tb', 'Bu', name='transferflags', metadata=MetaData())), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('trip_id', 'stop_id', 'stop_sequence', 'valid_from'),
    )
    op.create_table('gtfs_transfers',
        sa.Column('from_stop_id', sa.String(), nullable=False),
        sa.Column('to_stop_id', sa.String(), nullable=False),
        sa.Column('from_trip_id', sa.String(), nullable=False),
        sa.Column('to_trip_id', sa.String(), nullable=False),
        sa.Column('transfer_type', sa.Enum('RECOMMENDED', 'TIMED', 'MINIMUM_TIME', 'NOT_POSSIBLE', name='transfertype'), nullable=False),
        sa.Column('min_transfer_time', sa.Integer(), nullable=True),
        sa.Column('max_waiting_time', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('from_stop_id', 'to_stop_id', 'from_trip_id', 'to_trip_id', 'valid_from'),
    )
    op.create_table('gtfs_trip',
        sa.Column('trip_id', sa.String(), nullable=False),
        sa.Column('route_id', sa.String(), nullable=False),
        sa.Column('service_id', sa.String(), nullable=False),
        sa.Column('trip_headsign', sa.String(), nullable=True),
        sa.Column('trip_short_name', sa.String(), nullable=True),
        sa.Column('direction_id', sa.Enum('OUTBOUND', 'INBOUND', name='direction'), nullable=True),
        sa.Column('block_id', sa.String(), nullable=True),
        sa.Column('shape_id', sa.String(), nullable=True),
        sa.Column('wheelchair_accessible', sa.Enum('UNKNOWN', 'ACCESSIBLE', 'NOT_ACCESSIBLE', name='wheelchairaccessible'), nullable=True),
        sa.Column('bikes_allowed', sa.Enum('UNKNOWN', 'ALLOWED', 'NOT_ALLOWED', 'ALLOWED_NO_ENTRY_EXIT', 'ALLOWED_NO_ENTRY', 'ALLOWED_NO_EXIT', name='bikesallowed'), nullable=True),
        sa.Column('exceptional', sa.Enum('REGULAR', 'DEPOT_TRAM_OR_TOURIST_TRAIN', name='tripexceptional'), nullable=True),
        sa.Column('agency_id', sa.Integer(), nullable=True),
        sa.Column('headsign_icons', sa.ARRAY(sa.Enum('Ma', 'Mb', 'Mc', 'Md', 'Ra', 'Sb', 'Fu', 'Fe', 'Ap', 'Tr', 'Tb', 'Bu', name='transferflags', metadata=MetaData())), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('trip_id', 'valid_from'),
    )
    op.create_table('feed_info',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('feed_start_date', sa.Date(), nullable=False),
        sa.Column('applied_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feed_info_applied_at', 'feed_info', ['applied_at'])

    op.create_table('rt_operator',
        sa.Column('rt_operator_id', sa.Integer(), nullable=False),
        sa.Column('agency_id', sa.Integer(), nullable=True),
        sa.Column('operator_label', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('rt_operator_id'),
        sa.UniqueConstraint('operator_label'),
    )
    op.create_table('rt_vehicle_type',
        sa.Column('vehicle_type_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('vehicle_type_id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table('rt_vehicle',
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('registration_number', sa.String(), nullable=False),
        sa.Column('operator_id', sa.Integer(), nullable=True),
        sa.Column('vehicle_type_id', sa.Integer(), nullable=True),
        sa.Column('wheelchair_accessible', sa.Boolean(), nullable=True),
        sa.Column('air_conditioned', sa.Boolean(), nullable=True),
        sa.Column('usb_chargers', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['operator_id'], ['rt_operator.rt_operator_id']),
        sa.ForeignKeyConstraint(['vehicle_type_id'], ['rt_vehicle_type.vehicle_type_id']),
        sa.PrimaryKeyConstraint('vehicle_id'),
    )
    op.create_index(op.f('ix_rt_vehicle_registration_number'), 'rt_vehicle', ['registration_number'], unique=False)
    op.create_table('rt_trip',
        sa.Column('trip_id', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=True),
        sa.Column('feed_vehicle_id', sa.String(), nullable=True),
        sa.Column('schedule_relationship', sa.Enum('SCHEDULED', 'ADDED', 'UNSCHEDULED', 'CANCELED', 'REPLACEMENT', 'DUPLICATED', 'DELETED', 'NEW', name='schedulerelationship'), nullable=True),
        sa.Column('origin_route_name', sa.String(), nullable=True),
        sa.Column('run_number', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('additional_data_failed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vehicle_id'], ['rt_vehicle.vehicle_id']),
        sa.PrimaryKeyConstraint('trip_id', 'start_date'),
    )
    op.create_table('rt_stop_time',
        sa.Column('trip_id', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('stop_sequence', sa.Integer(), nullable=False),
        sa.Column('stop_id', sa.String(), nullable=False),
        sa.Column('arrival_delay', sa.Integer(), nullable=True),
        sa.Column('departure_delay', sa.Integer(), nullable=True),
        sa.Column('track_scheduled', sa.String(), nullable=True),
        sa.Column('track_actual', sa.String(), nullable=True),
        sa.Column('headsign', sa.String(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['trip_id', 'start_date'], ['rt_trip.trip_id', 'rt_trip.start_date']),
        sa.PrimaryKeyConstraint('trip_id', 'start_date', 'stop_sequence'),
    )

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

    op.execute("""
        CREATE OR REPLACE FUNCTION trip_schedule(p_date DATE, p_trip_id TEXT)
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

    op.execute("""
        CREATE OR REPLACE FUNCTION trip_run_info(p_date DATE, p_trip_id TEXT)
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

    op.execute("""
        CREATE OR REPLACE FUNCTION trip_runs(
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


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS trip_runs(DATE, TEXT, INT, INT)")
    op.execute("DROP FUNCTION IF EXISTS trip_run_info(DATE, TEXT)")
    op.execute("DROP FUNCTION IF EXISTS trip_schedule(DATE, TEXT)")
    op.execute("DROP FUNCTION IF EXISTS trip_schedule_at(date, text, text)")

    op.drop_table('rt_stop_time')
    op.drop_table('rt_trip')
    op.drop_index(op.f('ix_rt_vehicle_registration_number'), table_name='rt_vehicle')
    op.drop_table('rt_vehicle')
    op.drop_table('rt_vehicle_type')
    op.drop_table('rt_operator')
    op.drop_index('ix_feed_info_applied_at', table_name='feed_info')
    op.drop_table('feed_info')
    op.drop_table('gtfs_trip')
    op.drop_table('gtfs_transfers')
    op.drop_table('gtfs_stop_times')
    op.drop_table('gtfs_stop')
    op.drop_table('gtfs_shape')
    op.drop_table('gtfs_route_stop')
    op.drop_table('gtfs_route_agency')
    op.drop_table('gtfs_route')
    op.drop_table('gtfs_calendar_date')
    op.drop_table('gtfs_calendar')
    op.drop_table('gtfs_agency')
    op.execute("DROP TYPE IF EXISTS transferflags")
