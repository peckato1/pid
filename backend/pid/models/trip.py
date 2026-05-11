from sqlalchemy import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin, transfer_flags_sql
from pid.models.enums import BikesAllowed, Direction, TransferFlags, WheelchairAccessible, TripExceptional


class Trip(ValidityMixin, Base):
    __tablename__ = "gtfs_trip"

    trip_id: Mapped[str] = mapped_column(primary_key=True)
    route_id: Mapped[str]
    service_id: Mapped[str]
    trip_headsign: Mapped[str | None]
    trip_short_name: Mapped[str | None]
    direction_id: Mapped[Direction | None]
    block_id: Mapped[str | None]
    shape_id: Mapped[str | None]
    wheelchair_accessible: Mapped[WheelchairAccessible | None]
    bikes_allowed: Mapped[BikesAllowed | None]
    exceptional: Mapped[TripExceptional | None]
    agency_id: Mapped[int | None]
    headsign_icons: Mapped[list[TransferFlags] | None] = mapped_column(ARRAY(transfer_flags_sql))
