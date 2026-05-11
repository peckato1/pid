import datetime

from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin
from pid.models.enums import ExceptionType


class Calendar(ValidityMixin, Base):
    __tablename__ = "gtfs_calendar"

    service_id: Mapped[str] = mapped_column(primary_key=True)
    monday: Mapped[bool]
    tuesday: Mapped[bool]
    wednesday: Mapped[bool]
    thursday: Mapped[bool]
    friday: Mapped[bool]
    saturday: Mapped[bool]
    sunday: Mapped[bool]
    start_date: Mapped[datetime.date]
    end_date: Mapped[datetime.date]


class CalendarDate(ValidityMixin, Base):
    __tablename__ = "gtfs_calendar_date"

    service_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime.date] = mapped_column(primary_key=True)
    exception_type: Mapped[ExceptionType]
