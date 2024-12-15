
from enum import Enum
from typing import Any
from pydantic import BaseModel, computed_field, model_validator
from datetime import datetime, timezone, timedelta


tzinfo = timezone(timedelta(hours=3))


class OnboardingMessage(BaseModel):
    text: str


class AssistantMessage(OnboardingMessage):
    block_id: int


class BlockMessage(BaseModel):
    message: OnboardingMessage
    from_user: bool


class Action(str, Enum):
    SEND_MESSAGE = "send_message"
    REOPEN_CHAT = "reopen_chat"
    CLEAR_LAYER = "clear_layer"
    CHARGE_LIGHTS = "charge_lights"


class NextAction(BaseModel):
    action: Action | None
    meta: Any
    assistant_messages: list[AssistantMessage]


class UserAction(BaseModel):
    u_id: int
    action: Action
    message: OnboardingMessage | None
    created_at: datetime = datetime.now(tzinfo)

    @model_validator(mode='after')
    def validate_message(self):
        if self.action != Action.SEND_MESSAGE:
            self.message = None
        return self


class Onboarding(BaseModel):
    chat: list[BlockMessage]
    next_action: NextAction | None = None
