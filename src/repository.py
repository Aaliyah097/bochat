from typing import TypeVar, Generic, Any, Tuple, Type, Dict
import datetime
import pytz
from pydantic import BaseModel
from mongo_database import MongoDBClient


class Repository:
    messages_collection = "messages"
    lights_collection = "lights"
    onboardings_collection = "onboardings"
    mongo_client: MongoDBClient = MongoDBClient

    @classmethod
    async def create_indexes(cls):
        async with cls.mongo_client(cls.lights_collection) as collection:
            await collection.create_index(
                [("user_id", 1), ("chat_id", 1)],
                unique=True
            )

    @staticmethod
    def get_now() -> datetime.datetime:
        return datetime.datetime.now().astimezone(
            pytz.timezone('Europe/Moscow')).now()
