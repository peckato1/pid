import datetime

from sqlalchemy import Enum as _SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pid.models.enums import TransferFlags as _TF


class Base(DeclarativeBase):
    pass


class ValidityMixin:
    valid_from: Mapped[datetime.date] = mapped_column(primary_key=True)
    valid_until: Mapped[datetime.date | None]


# Shared SQL ENUM type for TransferFlags, attached to metadata so it's
# created/dropped exactly once even though several columns reference it.
transfer_flags_sql = _SAEnum(
    _TF,
    name="transferflags",
    values_callable=lambda x: [e.value for e in x],
    metadata=Base.metadata,
)


from pid.models.agency import Agency # noqa: F401, E402
from pid.models.feed_info import FeedInfo  # noqa: F401, E402
from pid.models.calendar import Calendar, CalendarDate  # noqa: F401, E402
from pid.models.route import Route, RouteStop, RouteAgency  # noqa: F401, E402
from pid.models.shapes import Shape  # noqa: F401, E402
from pid.models.stops import Stop  # noqa: F401, E402
from pid.models.stop_times import StopTime  # noqa: F401, E402
from pid.models.transfers import Transfer  # noqa: F401, E402
from pid.models.trip import Trip  # noqa: F401, E402
from pid.models.realtime import ActualStopTime, Operator, TripRun, Vehicle, VehicleType  # noqa: F401, E402
