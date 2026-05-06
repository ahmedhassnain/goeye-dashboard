from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from models.base import Base

class RawDns(Base):
    __tablename__ = "raw_dns"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    unit_id      = Column(Integer, ForeignKey("units.unit_id"), nullable=False)
    archive_date = Column(Date, nullable=False)
    ip_version   = Column(String, nullable=False)
    dtime        = Column(DateTime, nullable=True)
    nameserver   = Column(String, nullable=True)
    lookup_host  = Column(String, nullable=True)
    response_ip  = Column(String, nullable=True)
    rtt          = Column(Float, nullable=True)
    successes    = Column(Integer, nullable=True)
    failures     = Column(Integer, nullable=True)