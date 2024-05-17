from typing import TypeVar, Generic, Any, Tuple, Type, Dict
import datetime
import pytz
from pydantic import BaseModel
from mongo_database import MongoDBClient


class Repository:
    messages_collection = "messages"
    lights_collection = "lights"

    def __init__(self):
        self.mongo_client: MongoDBClient = MongoDBClient

    @staticmethod
    def get_now() -> datetime.datetime:
        return datetime.datetime.now().astimezone(
            pytz.timezone('Europe/Moscow')).now()
