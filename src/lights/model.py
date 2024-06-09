from enum import Enum
import random
from pydantic import BaseModel
from datetime import datetime
from src.messages.model import Message


class Operation(int, Enum):
    received = 1
    withdrawn = 0


class UsersLayer(int, Enum):
    first = 1
    second = 2
    friends = 3


class LightDTO(BaseModel):
    id: str | None = None
    user_id: int
    chat_id: int
    amount: int
    updated_at: datetime = datetime.now()

    def __init__(self, *args, **kwargs):
        _id = kwargs.get('_id') or kwargs.get('id')
        kwargs['id'] = str(_id) if _id else None
        super().__init__(*args, **kwargs)

    def __add__(self, other):
        self.amount += other.amount
        self.updated_at = datetime.now()

        return self


class Light:
    def to_dto(self) -> LightDTO:
        return LightDTO(
            user_id=self.user_id,
            chat_id=self.chat_id,
            amount=self.amount,
        )

    def __init__(self,
                 user_id: int,
                 chat_id: int,
                 message: Message,
                 prev_message: Message,
                 are_both_online: bool,
                 users_layer: UsersLayer):
        self.user_id: int = user_id
        self.chat_id: int = chat_id
        self.amount: int = 0
        self.total: int = 0
        self.operation: Operation = Operation.received

        self.message: Message = message
        self.prev_message: Message = prev_message
        self.are_both_online: bool = are_both_online
        self.users_layer: UsersLayer = users_layer

        self._analyze_message()
        if self.total > 0:
            self._random_lights()

    def _analyze_message(self) -> None:
        words = len(self.message.text.split()
                    ) if self.message and self.message.text else 0
        chars = len(
            self.message.text) if self.message and self.message.text else 0
        multiplier = 1 if (
            self.prev_message and self.prev_message.user_id != self.message.user_id) else 0

        try:
            self.total = int(words / 100 + chars / 20 + 2 * multiplier)
        except ZeroDivisionError:
            self.total = 0

        if self.are_both_online:
            self.total *= 2

    @staticmethod
    def roll(minutes, chance) -> int:
        if not minutes or not chance:
            return 0

        try:
            minutes = float(minutes)
            chance = float(chance)
        except ValueError:
            return 0

        if minutes >= 480:
            probabilities = {
                0: 0.1,
                1: 0.15,
                2: 0.25,
                3: 0.5
            }
        elif 30 <= minutes < 480:
            probabilities = {
                0: 0.1,
                1: 0.25,
                3: 0.3,
                2: 0.35,
            }
        else:
            probabilities = {
                3: 0.1,
                2: 0.15,
                1: 0.25,
                0: 0.5,
            }

        likes = 0
        for amount, prob in probabilities.items():
            likes = amount
            if chance <= prob:
                break

        return int(likes)

    def _random_lights(self):
        if self.message and self.message.created_at and self.prev_message and self.prev_message.created_at:
            time_diff = round((self.message.created_at - (
                self.prev_message.created_at if self.prev_message else datetime.now()
            )).seconds / 60, 0)
        else:
            time_diff = 0

        chance = random.random()
        if self.are_both_online:
            self.amount = self.roll(time_diff, chance)
            return

        if self.users_layer == 2:
            self.amount = self.roll(time_diff, chance)
        else:
            if chance <= 0.35:
                self.amount = random.randint(1, 3)
