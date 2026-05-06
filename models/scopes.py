from sqlalchemy import Column, Integer, String
from models.base import Base

class Scope(Base):
    __tablename__ = "scopes"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    scope_name          = Column(String, unique=True, nullable=False)
    operator_filter     = Column(String, nullable=True)
    technology_filter   = Column(String, nullable=True)