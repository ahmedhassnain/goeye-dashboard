from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from models.base import Base

class RawGameLatency(Base):
    __tablename__ = "raw_game_latency"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    unit_id      = Column(Integer, ForeignKey("units.unit_id"), nullable=False)
    app_key      = Column(String, ForeignKey("applications.file_key"), nullable=False)
    archive_date = Column(Date, nullable=False)
    dtime_local  = Column(DateTime, nullable=True)
    dtime_utc    = Column(DateTime, nullable=True)
    error_code   = Column(String, nullable=True)
    provider     = Column(String, nullable=True)
    region       = Column(String, nullable=True)
    datacenter   = Column(String, nullable=True)
    address      = Column(String, nullable=True)
    rtt_avg      = Column(Float, nullable=True)
    rtt_min      = Column(Float, nullable=True)
    rtt_max      = Column(Float, nullable=True)
    rtt_std      = Column(Float, nullable=True)
    hop_count    = Column(Integer, nullable=True)
    num_successes= Column(Integer, nullable=True)
    num_failures = Column(Integer, nullable=True)
    successes    = Column(Integer, nullable=True)
    failures     = Column(Integer, nullable=True)