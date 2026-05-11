from geoalchemy2 import Geometry
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base, ValidityMixin
from pid.models.enums import ZoneRegionType, StopLocationType, WheelchairBoarding


class Stop(ValidityMixin, Base):
    __tablename__ = "gtfs_stop"

    stop_id: Mapped[str] = mapped_column(primary_key=True)
    stop_name: Mapped[str | None]
    geometry: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326))
    zone_id: Mapped[str | None]
    stop_url: Mapped[str | None]
    location_type: Mapped[StopLocationType | None]
    parent_station_id: Mapped[str | None]
    wheelchair_boarding: Mapped[int | None]
    level_id: Mapped[str | None]
    platform_code: Mapped[str | None]
    asw_node_id: Mapped[int | None]  # Czech stop ID data
    asw_stop_id: Mapped[int | None]
    zone_region_type: Mapped[ZoneRegionType | None]

    def get_wheelchair_boarding(self) -> WheelchairBoarding | None:
        if self.wheelchair_boarding is None:
            return None
        if self.location_type == StopLocationType.ENTRANCE_EXIT:
            if self.wheelchair_boarding == 0:
                return WheelchairBoarding.UNKNOWN
            elif self.wheelchair_boarding == 1:
                return WheelchairBoarding.ENTRANCE_ACCESSIBLE
            elif self.wheelchair_boarding == 2:
                return WheelchairBoarding.NO_ACCESSIBLE_PATH_FROM_ENTRANCE_TO_PLATFORM
            else:
                raise ValueError(f"Invalid wheelchair_boarding {self.wheelchair_boarding} for entrance/exit")

        if self.wheelchair_boarding == 0:
            return WheelchairBoarding.UNKNOWN
        elif self.wheelchair_boarding == 1:
            return WheelchairBoarding.SOME_VEHICLES
        elif self.wheelchair_boarding == 2:
            return WheelchairBoarding.NOT_POSSIBLE
        else:
            raise ValueError(f"Invalid wheelchair_boarding {self.wheelchair_boarding}")
