from pydantic import BaseModel


class Device(BaseModel):
    token: str
    user_id: int
