from sqlalchemy import Column, Integer, String, Boolean
from models.base import Base

class Unit(Base):
    __tablename__ = "units"

    unit_id     = Column(Integer, primary_key=True)
    mac         = Column(String, nullable=True)
    unit_name   = Column(String, nullable=True)
    operator    = Column(String, nullable=True)
    technology  = Column(String, nullable=True)
    identifier  = Column(String, nullable=True)
    is_active   = Column(Boolean, default=True)