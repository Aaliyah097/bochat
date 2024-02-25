from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str
    created_at: datetime = datetime.now()
    is_edited: bool = False
    id: int | None = None
    reply_id: int | None = None
    is_read: bool = False
