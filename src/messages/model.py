from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str
    created_at: datetime = datetime.now()
    is_edited: bool = Field(default=False)
    id: str | None = None
    reply_id: int | None = None
    is_read: bool = Field(default=False)

    def __init__(self, *args, **kwargs):
        _id = kwargs.get('_id')
        kwargs['id'] = str(_id) if _id else None
        super().__init__(*args, **kwargs)

    def serialize(self) -> dict:
        return {
            str(k): str(v) for k, v in vars(self).items()
        }
