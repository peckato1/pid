from sqlalchemy import ARRAY, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin, transfer_flags_sql
from pid.models.enums import PickupType, DropOffType, TripOperationType, BikesAllowed, TransferFlags


class StopTime(ValidityMixin, Base):
    __tablename__ = "gtfs_stop_times"

    trip_id: Mapped[str] = mapped_column(primary_key=True)
    stop_id: Mapped[str] = mapped_column(primary_key=True)
    stop_sequence: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    arrival_time: Mapped[str | None] = mapped_column(String(8))
    departure_time: Mapped[str | None] = mapped_column(String(8))
    stop_headsign: Mapped[str | None]
    pickup_type: Mapped[PickupType] = mapped_column(server_default=PickupType.REGULAR.name)
    drop_off_type: Mapped[DropOffType] = mapped_column(server_default=DropOffType.REGULAR.name)
    shape_dist_traveled: Mapped[float | None]
    trip_operation_type: Mapped[TripOperationType | None]
    # PID feed extension: GTFS spec puts bikes_allowed on trips, not stop_times.
    bikes_allowed: Mapped[BikesAllowed | None]
    stop_icons: Mapped[list[TransferFlags] | None] = mapped_column(ARRAY(transfer_flags_sql))
    headsign_icons: Mapped[list[TransferFlags] | None] = mapped_column(ARRAY(transfer_flags_sql))
