import redis.asyncio as aioredis
from config import settings
from monitor import Monitor


class RedisPubSubManager:
    pool = aioredis.ConnectionPool.from_url(
        settings.conn_string
    )

    def __init__(self):
        self.redis_connection = None
        self.redis_connection = aioredis.Redis.from_pool(self.pool)
        self.pubsub = self.redis_connection.pubsub()

    async def publish(self, chat_id: str, message: str) -> None:
        await self.redis_connection.publish(chat_id, message)

    async def subscribe(self, chat_id: str):
        await self.pubsub.subscribe(chat_id)
        return self.pubsub

    async def unsubscribe(self, chat_id: str) -> None:
        await self.pubsub.unsubscribe(chat_id)


class RedisClient:
    pool = aioredis.ConnectionPool.from_url(
        settings.conn_string
    )
    redis_connection = None

    @classmethod
    async def connect(cls):
        cls.redis_connection = aioredis.Redis(connection_pool=cls.pool)
        await Monitor.log("Подключение к Редис открыто")

    @classmethod
    async def disconnect(cls):
        await cls.redis_connection.close()
        await Monitor.log("Подключение к Редис закрыто")

    async def __aenter__(self) -> 'Redis':
        return self.redis_connection

    async def __aexit__(self, *args):
        pass
