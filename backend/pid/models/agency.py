from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin


class Agency(ValidityMixin, Base):
    __tablename__ = "gtfs_agency"

    agency_id: Mapped[int] = mapped_column(primary_key=True)
    agency_name: Mapped[str]
