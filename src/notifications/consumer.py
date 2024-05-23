import time
import asyncio
from multiprocessing import Process, Event
import redis
from httpx import AsyncClient
from src.notifications.google_auth import get_access_token
from src.notifications.firebase import send_notification
from src.notifications.repo import DeviceRepo
from src.notifications.device import Device
from src.pubsub_manager import RedisClient
from src.messages.model import Message
from config import settings


class Consumer(Process):
    GROUP_NAME = 'mygroup'
    STREAN_NAME = 'notifications'

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.exit_event = Event()
        self.access_token = None
        self.token_created_at: int = 0
        self.device_repo: DeviceRepo = DeviceRepo()

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.main())

    async def _update_token(self) -> None:
        if (time.time() - self.token_created_at) >= settings.google_jwt_ttl:
            self.access_token = await get_access_token()
            self.token_created_at = time.time()

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
                await self._update_token()
                messages = await r.xreadgroup(self.GROUP_NAME, consumer_name, streams={self.STREAN_NAME: '>'}, count=1, noack=True)

                if messages:
                    stream, message = messages[0]
                    message_id, message_data = message[0]
                    message = Message.deserialize(message_data)
                    user_devices = await self.device_repo.get_user_devices(
                        message.recipient_id
                    ) if message.recipient_id else []
                    for device in user_devices:
                        await send_notification(
                            device.token,
                            title=f'Новое уведомление от {message.user_id}',
                            message=message.serialize(),
                            access_token=self.access_token
                        )

                    await r.xdel(self.STREAN_NAME, message_id)
                await asyncio.sleep(0.1)
