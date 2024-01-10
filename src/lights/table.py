from sqlalchemy import Column, Integer, DateTime, func, Boolean
from database import Base


class Lights(Base):
    __tablename__ = 'lights'

    id = Column(Integer, primary_key=True, unique=True, nullable=False, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)
    total = Column(Integer, nullable=False)
    operation = Column(Integer, nullable=False)
    acked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
