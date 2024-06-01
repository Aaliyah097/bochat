import time
import asyncio
import redis
from httpx import AsyncClient
from src.notifications.google_auth import get_access_token
from src.notifications.firebase import send_notification
from src.notifications.repo import DeviceRepo
from src.notifications.device import Device
from src.pubsub_manager import RedisClient
from src.messages.model import Message
from config import settings


class Consumer:
    GROUP_NAME = 'mygroup'
    STREAN_NAME = 'notifications'

    def __init__(self, consumers_amount: int = 3):
        super().__init__()
        self.access_token = None
        self.token_created_at: int = 0
        self.device_repo: DeviceRepo = DeviceRepo()
        self.is_active = True
        self.consumers_amount = consumers_amount

    async def _update_token(self) -> None:
        if (time.time() - self.token_created_at) >= settings.google_jwt_ttl:
            self.access_token = await get_access_token()
            self.token_created_at = time.time()

    async def main(self):
        # await RedisClient.connect()

        async with RedisClient() as r:
            try:
                await r.xgroup_create(self.STREAN_NAME, self.GROUP_NAME, id='$', mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP Consumer Group name already exists" in str(e):
                    pass

        await asyncio.gather(*[self._consume(f'consumer{i}') for i in range(1, self.consumers_amount + 1)])

    async def _consume(self, consumer_name: str):
        async with RedisClient() as r:
            while self.is_active:
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
                            title=f'Новое сообщение',
                            text=message.text,
                            data={
                                'user_id': str(message.user_id),
                                'chat_id': str(message.chat_id),
                                'created_at': str(message.created_at),
                                'id': str(message.id),
                                'recipient_id': str(message.recipient_id)
                            },
                            access_token=self.access_token
                        )

                    await r.xdel(self.STREAN_NAME, message_id)
                await asyncio.sleep(0.1)
