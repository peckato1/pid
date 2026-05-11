from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin
from pid.models.enums import TransferType


class Transfer(ValidityMixin, Base):
    __tablename__ = "gtfs_transfers"

    from_stop_id: Mapped[str] = mapped_column(primary_key=True)
    to_stop_id: Mapped[str] = mapped_column(primary_key=True)
    # Empty string means "not trip-specific"; NULL would prevent PK participation.
    from_trip_id: Mapped[str] = mapped_column(primary_key=True, default="")
    to_trip_id: Mapped[str] = mapped_column(primary_key=True, default="")
    transfer_type: Mapped[TransferType]
    min_transfer_time: Mapped[int | None]
    max_waiting_time: Mapped[int]
