from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from models.base import Base

class HourlyAggregate(Base):
    __tablename__ = "hourly_aggregates"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    scope_id              = Column(Integer, ForeignKey("scopes.id"), nullable=False)
    agg_date              = Column(Date, nullable=False)
    hour                  = Column(Integer, nullable=False)
    category              = Column(String, nullable=False)
    fail_rate_pct         = Column(Float, nullable=True)
    disconnection_minutes = Column(Float, nullable=True)