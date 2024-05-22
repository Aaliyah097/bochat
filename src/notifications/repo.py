from src.pubsub_manager import RedisClient
from src.notifications.device import Device


class DeviceRepo:
    token_key: str = '%stokens'

    async def store_device(self, device: Device) -> None:
        async with RedisClient() as r:
            await r.sadd(self.token_key % str(device.user_id), device.token)

    async def get_user_devices(self, user_id: int) -> list[Device]:
        async with RedisClient() as r:
            return [
                Device(
                    user_id=user_id,
                    token=t
                )
                for t in await r.smembers(self.token_key % str(user_id))
            ]
