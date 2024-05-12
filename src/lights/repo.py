from bson.objectid import ObjectId
from typing import List, Union
import json
from sqlalchemy.sql import select
from src.repository import Repository
from src.lights.table import Lights
from src.lights.model import LightDTO, Operation
from src.pubsub_manager import RedisClient


class LightsRepo(Repository):
    # redis
    async def get_last_user_light(self, user_id: int, chat_id: int) -> Union[LightDTO, None]:
        if not user_id or not chat_id:
            return None

        user_id, chat_id = str(user_id), str(chat_id)

        async with RedisClient() as client:
            res = await client.get(f"last_light_{user_id}_{chat_id}")
            return LightDTO.model_validate_json(res.decode("utf-8")) if res else None

    # redis
    async def store_last_user_light(self, user_id: int, chat_id: int, light: LightDTO):
        if not all([user_id, chat_id, light]):
            return

        if not isinstance(light, LightDTO):
            return

        user_id, chat_id = str(user_id), str(chat_id)

        async with RedisClient() as client:
            await client.set(f"last_light_{user_id}_{chat_id}", light.model_dump_json())

    # mongo
    async def get_free(self, chat_id: int, user_id: int) -> List[LightDTO]:
        if not user_id or not chat_id:
            return []

        try:
            chat_id, user_id = int(chat_id), int(user_id)
        except ValueError:
            return []

        lights = []
        async with self.mongo_client(self.lights_collection) as collection:
            result = collection.find(
                {
                    'chat_id': chat_id,
                    'user_id': user_id
                }
            )
            async for doc in result:
                lights.append(
                    LightDTO(**doc)
                )
        return lights

    # mongo
    async def override(self, prev_light: LightDTO, light: LightDTO):
        if not prev_light or not light:
            return

        if not isinstance(prev_light, LightDTO) or not isinstance(light, LightDTO):
            return

        prev_light += light
        async with self.mongo_client(self.lights_collection) as collection:
            await collection.update_one(
                {'_id': prev_light.id}, {"$set": prev_light.model_dump()}
            )

    # mongo + redis
    async def save_up(self, light: LightDTO) -> LightDTO | None:
        if not light:
            return

        if not isinstance(light, LightDTO):
            return

        light.operation = Operation.received
        light.acked = True

        prev_light = await self.get_last_user_light(light.user_id, light.chat_id)

        if prev_light and light.amount == 0:
            await self.override(prev_light, light)

        if light.amount != 0:
            light.acked = False

        if prev_light:
            light += prev_light

        async with self.mongo_client(self.lights_collection) as collection:
            result = await collection.insert_one(light.model_dump())
            light.created_at = self.get_now()
            light.id = str(result.inserted_id)

        await self.store_last_user_light(light.user_id, light.chat_id, light)

        if light.amount != 0:
            return light

    # mongo + redis
    async def withdrawn(self, light_id: str):
        if not light_id:
            return

        light_id = str(light_id)

        async with self.mongo_client(self.lights_collection) as collection:
            result = await collection.find_one({'_id': ObjectId(light_id)})

            if not result:
                raise Exception("Лайт не найден")

            light = LightDTO(**result)

            prev_light = await self.get_last_user_light(light.user_id, light.chat_id)

            if prev_light.total < light.amount:
                raise Exception("Недостаточно лайтов")

            light.acked = True

            new_light = {
                "user_id": light.user_id,
                "chat_id": light.chat_id,
                "amount": light.amount,
                "total": prev_light.total - light.amount,
                "operation": Operation.withdrawn,
                "acked": True
            }

            await collection.insert_one(new_light)

    # redis
    async def calc_amount(self, user_id: int, chat_id: int) -> int:
        if not user_id or not chat_id:
            return 0

        try:
            chat_id, user_id = int(chat_id), int(user_id)
        except ValueError:
            return 0

        prev_light = await self.get_last_user_light(user_id, chat_id)
        return prev_light.total if prev_light else 0
