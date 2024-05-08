import random
import json
import aiormq
from config import settings


class RabbitMQPool:
    connection = None

    def __init__(self, max_channels: int = 1,
                 queue_name: str = "notifications",
                 exchange_name: str = "",
                 routing_key: str = "notifications"):
        self.max_channels = max_channels
        self.channels: list[aiormq.channel.AbstractChannel] = []
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.routing_key = routing_key

    def __new__(cls, *args, **kwargs):
        if hasattr(cls, 'instance'):
            return cls.instance
        instance = super().__new__(cls)
        cls.instance = instance
        return instance

    async def connect(self):
        self.connection = await aiormq.connect(settings.rabbitmq_conn_string)
        for _ in range(self.max_channels):
            self.channels.append(await self.connection.channel())
        await self.channels[0].queue_declare(self.queue_name)

    async def publish_message(self, message: dict):
        await random.choice(self.channels).basic_publish(
            body=json.dumps(message).encode('utf-8'),
            exchange=self.exchange_name,
            routing_key=self.routing_key
        )

    async def close(self):
        await self.connection.close()
        for channel in self.channels:
            await channel.close()


rabbitmq_pool = RabbitMQPool()
