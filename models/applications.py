# applications.py
from sqlalchemy import Column, Integer, String
from models.base import Base

class Application(Base):
    __tablename__ = "applications"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    file_key    = Column(String, unique=True, nullable=False)
    app_name    = Column(String, nullable=False)
    category    = Column(String, nullable=False)