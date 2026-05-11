import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from pid.models import Base


class FeedInfo(Base):
    __tablename__ = "feed_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_start_date: Mapped[datetime.date]
    applied_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
