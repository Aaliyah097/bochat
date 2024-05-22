import random
import json
import aiormq
from config import settings


class RabbitMQPool:
    connection = None
    channels: list[aiormq.channel.AbstractChannel] = []
    default_queue = "notifications"

    def __init__(self, max_channels: int = 1,
                 queue_name: str = "notifications",
                 exchange_name: str = "",
                 routing_key: str = "notifications"):
        self.max_channels = max_channels
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.routing_key = routing_key

    @classmethod
    async def connect(cls):
        cls.connection = await aiormq.connect(settings.rabbitmq_conn_string)
        for _ in range(self.max_channels):
            cls.channels.append(await cls.connection.channel())
        await cls.channels[0].queue_declare(cls.default_queue)

    @classmethod
    async def declare_queue(cls, queue_name: str):
        if self.channels:
            await cls.channels[0].queue_declare(cls.queue_name)

    async def publish_message(self, message: dict):
        await random.choice(self.channels).basic_publish(
            body=json.dumps(message).encode('utf-8'),
            exchange=self.exchange_name,
            routing_key=self.routing_key
        )

    @classmethod
    async def close(cls):
        await cls.connection.close()
        for channel in cls.channels:
            await channel.close()
