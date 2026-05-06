from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from models.base import Base

class RawSocialMedia(Base):
    __tablename__ = "raw_social_media"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    unit_id         = Column(Integer, ForeignKey("units.unit_id"), nullable=False)
    archive_date    = Column(Date, nullable=False)
    dtime_local     = Column(DateTime, nullable=True)
    dtime_utc       = Column(DateTime, nullable=True)
    error_code      = Column(String, nullable=True)
    service         = Column(String, nullable=True)
    media           = Column(String, nullable=True)
    direction       = Column(String, nullable=True)
    target          = Column(String, nullable=True)
    address         = Column(String, nullable=True)
    rtt_avg         = Column(Float, nullable=True)
    rtt_median      = Column(Float, nullable=True)
    rtt_min         = Column(Float, nullable=True)
    rtt_max         = Column(Float, nullable=True)
    rtt_std         = Column(Float, nullable=True)
    successes       = Column(Integer, nullable=True)
    failures        = Column(Integer, nullable=True)