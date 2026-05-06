from sqlalchemy import Column, Integer, String, Boolean
from models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, autoincrement = True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="admin")


