from sqlalchemy import Column, Integer, Float, String, Date, DateTime, ForeignKey
from models.base import Base

class RawDisconnection(Base):
    __tablename__ = "raw_disconnection"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    unit_id      = Column(Integer, ForeignKey("units.unit_id"), nullable=False)
    archive_date = Column(Date, nullable=False)
    dtime        = Column(DateTime, nullable=True)
    end_dtime    = Column(DateTime, nullable=True)
    target       = Column(String, nullable=True)
    address      = Column(String, nullable=True)
    duration     = Column(Float, nullable=True)