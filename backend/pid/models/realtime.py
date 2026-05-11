import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base
from pid.models.enums import ScheduleRelationship


class Operator(Base):
    __tablename__ = "rt_operator"

    rt_operator_id: Mapped[int] = mapped_column(primary_key=True)
    agency_id: Mapped[int | None]
    operator_label: Mapped[str] = mapped_column(unique=True)


class TripRun(Base):
    __tablename__ = "rt_trip"

    trip_id: Mapped[str] = mapped_column(primary_key=True)
    start_date: Mapped[datetime.date] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("rt_vehicle.vehicle_id"))
    feed_vehicle_id: Mapped[str | None]
    schedule_relationship: Mapped[ScheduleRelationship | None]
    origin_route_name: Mapped[str | None]
    run_number: Mapped[int | None]
    updated_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    additional_data_failed_at: Mapped[datetime.datetime | None]


class ActualStopTime(Base):
    __tablename__ = "rt_stop_time"

    trip_id: Mapped[str] = mapped_column(primary_key=True)
    start_date: Mapped[datetime.date] = mapped_column(primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(primary_key=True)
    stop_id: Mapped[str]
    arrival_delay: Mapped[int | None]
    departure_delay: Mapped[int | None]
    track_scheduled: Mapped[str | None]
    track_actual: Mapped[str | None]
    headsign: Mapped[str | None]
    updated_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["trip_id", "start_date"],
            ["rt_trip.trip_id", "rt_trip.start_date"],
        ),
    )


class VehicleType(Base):
    __tablename__ = "rt_vehicle_type"

    vehicle_type_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class Vehicle(Base):
    __tablename__ = "rt_vehicle"

    vehicle_id: Mapped[int] = mapped_column(primary_key=True)
    registration_number: Mapped[str] = mapped_column(index=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("rt_operator.rt_operator_id"))
    vehicle_type_id: Mapped[int | None] = mapped_column(ForeignKey("rt_vehicle_type.vehicle_type_id"))
    wheelchair_accessible: Mapped[bool | None]
    air_conditioned: Mapped[bool | None]
    usb_chargers: Mapped[bool | None]
