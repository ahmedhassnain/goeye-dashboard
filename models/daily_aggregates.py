from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from models.base import Base

class DailyAggregate(Base):
    __tablename__ = "daily_aggregates"

    id                       = Column(Integer, primary_key=True, autoincrement=True)
    scope_id                 = Column(Integer, ForeignKey("scopes.id"), nullable=False)
    agg_date                 = Column(Date, nullable=False)
    category                 = Column(String, nullable=False)
    reliability_pct          = Column(Float, nullable=True)
    weighted_reliability_pct = Column(Float, nullable=True)
    uptime_pct               = Column(Float, nullable=True)
    total_tests              = Column(Integer, nullable=True)
    total_disconnections     = Column(Integer, nullable=True)
    median_disconnection_sec = Column(Float, nullable=True)
    dns_v4_reliability       = Column(Float, nullable=True)
    dns_v6_reliability       = Column(Float, nullable=True)
    dns_v4_rtt_p50           = Column(Float, nullable=True)
    dns_v6_rtt_p50           = Column(Float, nullable=True)