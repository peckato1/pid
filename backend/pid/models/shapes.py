from geoalchemy2 import Geometry
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin


class Shape(ValidityMixin, Base):
    __tablename__ = "gtfs_shape"

    shape_id: Mapped[str] = mapped_column(primary_key=True)
    geometry: Mapped[str] = mapped_column(Geometry("LINESTRING", srid=4326))
