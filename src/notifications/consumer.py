import asyncio
from multiprocessing import Process, Event
import redis
from httpx import AsyncClient
from src.notifications.google_auth import get_access_token
from src.notifications.firebase import send_notification
from src.notifications.repo import DeviceRepo
from src.pubsub_manager import RedisClient


class Consumer(Process):
    GROUP_NAME = 'mygroup'
    STREAN_NAME = 'notifications'

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.exit_event = Event()

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main())

    async def main(self, consumers_amount: int = 3):
        await RedisClient.connect()

        async with RedisClient() as r:
            try:
                await r.xgroup_create(self.STREAN_NAME, self.GROUP_NAME, id='$', mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP Consumer Group name already exists" in str(e):
                    pass

        await asyncio.gather(*[self._consume(f'consumer{i}') for i in range(1, consumers_amount + 1)])

    async def _consume(self, consumer_name: str):
        async with RedisClient() as r:
            while True:
                messages = await r.xreadgroup(self.GROUP_NAME, consumer_name, streams={self.STREAN_NAME: '>'}, count=1, noack=True)

                if messages:
                    stream, message = messages[0]
                    message_id, message_data = message[0]

                    message =

                await asyncio.sleep(1)
