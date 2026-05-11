import csv
import enum as _enum
import io
import logging
import zipfile
from datetime import date, datetime

from sqlalchemy import Enum as _SAEnum, select, text
from sqlalchemy.orm import Session

from pid import models
from pid.models.feed_info import FeedInfo

logger = logging.getLogger(__name__)

BATCH_SIZE = 10_000


def _s(v: str) -> str | None:
    return v if v != "" else None


def _i(v: str) -> int | None:
    return int(v) if v != "" else None


def _f(v: str) -> float | None:
    return float(v) if v != "" else None


def _b(v: str) -> bool | None:
    return (v == "1") if v != "" else None


def _flags(v: str) -> list[str] | None:
    if v == "":
        return None
    return [v[i : i + 2] for i in range(0, len(v), 2)]


def _d(v: str) -> date | None:
    return datetime.strptime(v, "%Y%m%d").date() if v != "" else None


def _open_csv(zf: zipfile.ZipFile, name: str):
    return csv.DictReader(io.TextIOWrapper(zf.open(name), encoding="utf-8-sig"))


def read_feed_start_date(zf: zipfile.ZipFile) -> date:
    for row in _open_csv(zf, "feed_info.txt"):
        return datetime.strptime(row["feed_start_date"], "%Y%m%d").date()
    raise ValueError("feed_info.txt is empty")


def _diff(
    session: Session,
    model,
    natural_keys: list[str],
    new_rows: list[dict],
    valid_from: date,
) -> None:
    """SCD Type 2 diff: insert new/changed rows, close deleted/superseded ones.

    All diffing is done in SQL via a temp table to avoid loading large result
    sets into Python (stop_times can be ~1.6 M rows).
    """
    tbl = model.__table__
    tname = tbl.name
    temp = f"_sync_{tname}"

    # Columns that carry actual data — validity bookkeeping columns are excluded
    # because they are managed here, not sourced from the feed.
    data_cols = [c.name for c in tbl.columns if c.name not in ("valid_from", "valid_until")]
    # Non-key columns are the ones we compare to detect changes.
    non_nk_cols = [c for c in data_cols if c not in natural_keys]

    # PostgreSQL stores IntEnum values by their Python name ('Added', not 1).
    # Row functions return raw ints, so we convert them here before any SQL
    # insert — otherwise psycopg sends an integer to a PostgreSQL enum column
    # and the cast fails.
    int_enum_cols = {
        c.name: c.type.enum_class
        for c in tbl.columns
        if c.name in data_cols
        and isinstance(c.type, _SAEnum)
        and c.type.enum_class is not None
        and issubclass(c.type.enum_class, _enum.IntEnum)
    }
    if int_enum_cols:
        converted = []
        for row in new_rows:
            r = dict(row)
            for col, cls in int_enum_cols.items():
                if r.get(col) is not None:
                    r[col] = cls(r[col]).name
            converted.append(r)
        new_rows = converted

    # SQL fragments for joining temp table to the main table on the natural key.
    nk_join = " AND ".join(f'"{temp}".{k} = {tname}.{k}' for k in natural_keys)
    # Same join but aliased to 'new_ver' — used to detect that a replacement
    # row was already inserted in this same run.
    nk_join_new = " AND ".join(f'new_ver.{k} = {tname}.{k}' for k in natural_keys)
    # IS NOT DISTINCT FROM handles NULLs correctly (NULL = NULL is true here).
    # PostGIS geometry's "=" only compares bounding boxes, so for geometry
    # columns we cast to bytea for byte-exact equality.
    geom_cols = {
        c.name for c in tbl.columns
        if c.name in non_nk_cols and c.type.__class__.__name__ == "Geometry"
    }
    same_check = " AND ".join(
        (
            f'{tname}.{c}::bytea IS NOT DISTINCT FROM "{temp}".{c}::bytea'
            if c in geom_cols
            else f'{tname}.{c} IS NOT DISTINCT FROM "{temp}".{c}'
        )
        for c in non_nk_cols
    ) or "TRUE"

    # Temp table mirrors the data columns of the target table (no validity cols).
    # WHERE FALSE copies the schema without any rows.
    session.execute(text(
        f'CREATE TEMP TABLE "{temp}" AS '
        f'SELECT {", ".join(data_cols)} FROM {tname} WHERE FALSE'
    ))

    # COPY is orders of magnitude faster than batched INSERTs for large tables.
    raw_conn = session.connection().connection
    with raw_conn.cursor().copy(f'COPY "{temp}" ({", ".join(data_cols)}) FROM STDIN') as copy:
        for row in new_rows:
            copy.write_row([row[c] for c in data_cols])

    # An index on the natural key lets the NOT EXISTS / EXISTS subqueries in the
    # diff steps below use index scans instead of sequential scans on the temp table.
    session.execute(text(
        f'CREATE INDEX ON "{temp}" ({", ".join(natural_keys)})'
    ))

    # Insert rows that are either new or changed. A row is considered unchanged
    # when an identical current record (valid_until IS NULL) already exists.
    session.execute(text(f"""
        INSERT INTO {tname} ({", ".join(data_cols)}, valid_from)
        SELECT {", ".join(f'"{temp}".{c}' for c in data_cols)}, :vf
        FROM "{temp}"
        WHERE NOT EXISTS (
            SELECT 1 FROM {tname}
            WHERE valid_until IS NULL AND {nk_join} AND {same_check}
        )
    """), {"vf": valid_from})

    # Close the previous version of every row that was deleted from the feed
    # or was superseded by a changed version inserted just above.
    # Guard `valid_from != :vf` prevents closing rows we just inserted.
    session.execute(text(f"""
        UPDATE {tname} SET valid_until = :vf
        WHERE valid_until IS NULL AND valid_from != :vf
        AND (
            NOT EXISTS (SELECT 1 FROM "{temp}" WHERE {nk_join})
            OR EXISTS (
                SELECT 1 FROM {tname} new_ver
                WHERE new_ver.valid_from = :vf AND new_ver.valid_until IS NULL
                AND {nk_join_new}
            )
        )
    """), {"vf": valid_from})

    session.execute(text(f'DROP TABLE IF EXISTS "{temp}"'))


def _rows_agency(zf: zipfile.ZipFile) -> list[dict]:
    seen = {}
    for r in _open_csv(zf, "route_sub_agencies.txt"):
        aid = int(r["sub_agency_id"])
        if aid not in seen:
            seen[aid] = {"agency_id": aid, "agency_name": r["sub_agency_name"]}
    return list(seen.values())


def _rows_calendar(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "service_id": r["service_id"],
            "monday": r["monday"] == "1",
            "tuesday": r["tuesday"] == "1",
            "wednesday": r["wednesday"] == "1",
            "thursday": r["thursday"] == "1",
            "friday": r["friday"] == "1",
            "saturday": r["saturday"] == "1",
            "sunday": r["sunday"] == "1",
            "start_date": _d(r["start_date"]),
            "end_date": _d(r["end_date"]),
        }
        for r in _open_csv(zf, "calendar.txt")
    ]


def _rows_calendar_dates(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "service_id": r["service_id"],
            "date": _d(r["date"]),
            "exception_type": int(r["exception_type"]),
        }
        for r in _open_csv(zf, "calendar_dates.txt")
    ]


def _rows_stops(zf: zipfile.ZipFile) -> list[dict]:
    def _point(lat: str, lon: str) -> str | None:
        if lat == "" or lon == "":
            return None
        return f"SRID=4326;POINT({float(lon)} {float(lat)})"
    return [
        {
            "stop_id": r["stop_id"],
            "stop_name": _s(r["stop_name"]),
            "geometry": _point(r["stop_lat"], r["stop_lon"]),
            "zone_id": _s(r["zone_id"]),
            "stop_url": _s(r["stop_url"]),
            "location_type": _i(r["location_type"]),
            "parent_station_id": _s(r["parent_station"]),
            "wheelchair_boarding": _i(r["wheelchair_boarding"]),
            "level_id": _s(r["level_id"]),
            "platform_code": _s(r["platform_code"]),
            "asw_node_id": _i(r["asw_node_id"]),
            "asw_stop_id": _i(r["asw_stop_id"]),
            "zone_region_type": _i(r["zone_region_type"]),
        }
        for r in _open_csv(zf, "stops.txt")
    ]


def _rows_routes(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "route_id": r["route_id"],
            "route_short_name": _s(r["route_short_name"]),
            "route_long_name": _s(r["route_long_name"]),
            "route_type": _i(r["route_type"]),
            "route_url": _s(r["route_url"]),
            "route_color": _s(r["route_color"]),
            "route_text_color": _s(r["route_text_color"]),
            "is_night": _b(r["is_night"]),
            "is_regional": _b(r["is_regional"]),
            "is_substitute_transport": _b(r["is_substitute_transport"]),
        }
        for r in _open_csv(zf, "routes.txt")
    ]


def _rows_route_agencies(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "route_id": r["route_id"],
            "agency_id": int(r["sub_agency_id"]),
            "route_licence_number": _i(r["route_licence_number"]),
        }
        for r in _open_csv(zf, "route_sub_agencies.txt")
    ]


def _rows_shapes(zf: zipfile.ZipFile) -> list[dict]:
    # GTFS gives one row per polyline point; we collapse them into one
    # LINESTRING per shape_id. WKT order is "lon lat", not "lat lon".
    points: dict[str, list[tuple[int, float, float]]] = {}
    for r in _open_csv(zf, "shapes.txt"):
        points.setdefault(r["shape_id"], []).append((
            int(r["shape_pt_sequence"]),
            float(r["shape_pt_lon"]),
            float(r["shape_pt_lat"]),
        ))
    rows = []
    for shape_id, pts in points.items():
        pts.sort()
        coords = ", ".join(f"{lon} {lat}" for _, lon, lat in pts)
        rows.append({
            "shape_id": shape_id,
            "geometry": f"SRID=4326;LINESTRING({coords})",
        })
    return rows


def _rows_trips(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "trip_id": r["trip_id"],
            "route_id": r["route_id"],
            "service_id": r["service_id"],
            "trip_headsign": _s(r["trip_headsign"]),
            "trip_short_name": _s(r["trip_short_name"]),
            "direction_id": _i(r["direction_id"]),
            "block_id": _s(r["block_id"]),
            "shape_id": _s(r["shape_id"]),
            "wheelchair_accessible": _i(r["wheelchair_accessible"]),
            "bikes_allowed": _i(r["bikes_allowed"]),
            "exceptional": _i(r["exceptional"]),
            "agency_id": _i(r["sub_agency_id"]),
            "headsign_icons": _flags(r["headsign_icons"]),
        }
        for r in _open_csv(zf, "trips.txt")
    ]


def _rows_stop_times(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "trip_id": r["trip_id"],
            "stop_id": r["stop_id"],
            "stop_sequence": int(r["stop_sequence"]),
            "arrival_time": _s(r["arrival_time"]),
            "departure_time": _s(r["departure_time"]),
            "stop_headsign": _s(r["stop_headsign"]),
            # GTFS spec: missing pickup/drop_off type means "regular" (0).
            "pickup_type": _i(r["pickup_type"]) or 0,
            "drop_off_type": _i(r["drop_off_type"]) or 0,
            "shape_dist_traveled": _f(r["shape_dist_traveled"]),
            "trip_operation_type": _i(r["trip_operation_type"]),
            "bikes_allowed": _i(r["bikes_allowed"]),
            "stop_icons": _flags(r["stop_icons"]),
            "headsign_icons": _flags(r["headsign_icons"]),
        }
        for r in _open_csv(zf, "stop_times.txt")
    ]


def _rows_route_stops(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "route_id": r["route_id"],
            "direction_id": int(r["direction_id"]),
            "stop_sequence": int(r["stop_sequence"]),
            "stop_id": r["stop_id"],
        }
        for r in _open_csv(zf, "route_stops.txt")
    ]


def _rows_transfers(zf: zipfile.ZipFile) -> list[dict]:
    return [
        {
            "from_stop_id": r["from_stop_id"],
            "to_stop_id": r["to_stop_id"],
            "transfer_type": int(r["transfer_type"]),
            "min_transfer_time": _i(r["min_transfer_time"]),
            "from_trip_id": r["from_trip_id"],
            "to_trip_id": r["to_trip_id"],
            "max_waiting_time": int(r["max_waiting_time"]),
        }
        for r in _open_csv(zf, "transfers.txt")
    ]


_TABLES: list[tuple] = [
    (models.Agency, ["agency_id"], _rows_agency),
    (models.Calendar, ["service_id"], _rows_calendar),
    (models.CalendarDate, ["service_id", "date"], _rows_calendar_dates),
    (models.Stop, ["stop_id"], _rows_stops),
    (models.Route, ["route_id"], _rows_routes),
    (models.RouteAgency, ["route_id", "agency_id"], _rows_route_agencies),
    (models.Shape, ["shape_id"], _rows_shapes),
    (models.Trip, ["trip_id"], _rows_trips),
    (models.StopTime, ["trip_id", "stop_id", "stop_sequence"], _rows_stop_times),
    (models.RouteStop, ["route_id", "direction_id", "stop_sequence"], _rows_route_stops),
    (models.Transfer, ["from_stop_id", "to_stop_id", "from_trip_id", "to_trip_id"], _rows_transfers),
]


def synced_today(session: Session) -> bool:
    """True if a successful sync was recorded today (server clock)."""
    latest = session.execute(
        select(FeedInfo.applied_at).order_by(FeedInfo.applied_at.desc()).limit(1)
    ).scalar()
    return latest is not None and latest.date() == date.today()


def sync(session: Session, zf: zipfile.ZipFile) -> None:
    valid_from = read_feed_start_date(zf)
    logger.info("Syncing GTFS feed valid from %s", valid_from)
    for model, natural_keys, rows_fn in _TABLES:
        table = model.__tablename__
        logger.debug("Loading %s from ZIP...", table)
        rows = rows_fn(zf)
        logger.debug("Loaded %d rows for %s, diffing...", len(rows), table)
        _diff(session, model, natural_keys, rows, valid_from)
        logger.info("Synced %s (%d rows)", table, len(rows))
    session.add(FeedInfo(feed_start_date=valid_from))
    session.commit()
    logger.info("Sync complete")
