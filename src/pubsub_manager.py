import redis.asyncio as aioredis
from config import settings
from monitor import Monitor


class RedisClient:
    pool = aioredis.ConnectionPool.from_url(
        settings.conn_string
    )
    redis_connection = None

    @classmethod
    async def connect(cls):
        if not cls.redis_connection:
            cls.redis_connection = aioredis.Redis(connection_pool=cls.pool)
        await Monitor.log("Подключение к Редис открыто")

    @classmethod
    async def disconnect(cls):
        if cls.redis_connection:
            await cls.redis_connection.close()
        if cls.pool:
            await cls.pool.disconnect()
        await Monitor.log("Подключение к Редис закрыто")

    async def __aenter__(self) -> 'Redis':
        return self.redis_connection

    async def __aexit__(self, *args):
        pass
