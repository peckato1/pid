from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin
from pid.models.enums import RouteType


class Route(ValidityMixin, Base):
    __tablename__ = "gtfs_route"

    route_id: Mapped[str] = mapped_column(primary_key=True)
    route_short_name: Mapped[str | None]
    route_long_name: Mapped[str | None]
    route_type: Mapped[RouteType | None]
    route_url: Mapped[str | None]
    route_color: Mapped[str | None] = mapped_column(String(6))
    route_text_color: Mapped[str | None] = mapped_column(String(6))
    is_night: Mapped[bool | None]
    is_regional: Mapped[bool | None]
    is_substitute_transport: Mapped[bool | None]


class RouteStop(ValidityMixin, Base):
    "Experimental data: Typical route for given route and direction"

    __tablename__ = "gtfs_route_stop"

    route_id: Mapped[str] = mapped_column(primary_key=True)
    direction_id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    stop_id: Mapped[str]


class RouteAgency(ValidityMixin, Base):
    __tablename__ = "gtfs_route_agency"

    route_id: Mapped[str] = mapped_column(primary_key=True)
    agency_id: Mapped[int] = mapped_column(primary_key=True)
    route_licence_number: Mapped[int | None]
