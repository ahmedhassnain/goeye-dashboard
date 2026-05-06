from sqlalchemy import Column, Integer, ForeignKey
from models.base import Base

class ScopeUnit(Base):
    __tablename__ = "scope_units"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    scope_id = Column(Integer, ForeignKey("scopes.id"), nullable=False)
    unit_id  = Column(Integer, ForeignKey("units.unit_id"), nullable=False)