import json
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
    recipient_id: int | None = None

    def __init__(self, *args, **kwargs):
        _id = kwargs.get('_id') or kwargs.get('id')
        kwargs['id'] = str(_id) if _id else None
        super().__init__(*args, **kwargs)

    def serialize(self) -> dict:
        return {
            'user_id': self.user_id or 0,
            'chat_id': self.chat_id or 0,
            'text': self.text or '',
            'created_at': str(self.created_at) or '',
            'is_edited': str(self.is_edited) or 'False',
            'id': self.id or 0,
            'reply_id': self.reply_id or 0,
            'is_read': str(self.is_read) or 'False',
            'recipient_id': str(self.recipient_id) or 0
        }

    @staticmethod
    def deserialize(payload: dict[bytes, bytes]) -> 'Message':
        return Message(**{
            k.decode('utf-8'): v.decode('utf-8') for k, v in payload.items()
        })

    def json_dumps(self) -> str:
        return json.dumps(self.serialize())

    @staticmethod
    def json_loads(payload: bytes) -> 'Message':
        return Message(**{
            k: v for k, v in json.loads(payload).items()
        })
