import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class UserTypeEnum(enum.Enum):
    admin = "admin"
    normal = "normal"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(Enum(UserTypeEnum), default=UserTypeEnum.normal, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
