from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from database import Base


class Messages(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, unique=True, nullable=False, autoincrement=True)
    text = Column(String(512), nullable=False, )
    user_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, nullable=False)
    reply_id = Column(Integer, nullable=True, default=None)
    is_edited = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
