from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str
    created_at: datetime = datetime.now()
    is_edited: bool = Field(default=False)
    id: int | None = None
    reply_id: int | None = None
    is_read: bool = Field(default=False)
