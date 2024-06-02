from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from config import settings
from monitor import Monitor
import asyncio


class MongoDBClient:
    client = None
    lock = asyncio.Lock()

    def __init__(self, collection: str):
        self.collection = collection

    async def __aenter__(self) -> AsyncIOMotorCollection:
        async with self.lock:
            db = self.client.get_default_database()
            return db[self.collection]

    async def __aexit__(self, *args):
        pass

    @classmethod
    async def connect(cls):
        async with cls.lock:
            if not cls.client:
                cls.client = AsyncIOMotorClient(settings.mongodb_conn_string)
            await Monitor.log("Подключение к Монге открыто")

    @classmethod
    async def disconnect(cls):
        async with cls.lock:
            if cls.client:
                cls.client.close()
            await Monitor.log("Подключение к Монге закрыто")
