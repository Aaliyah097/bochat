from bson.objectid import ObjectId
from typing import List, Union
import json
import datetime
from sqlalchemy.sql import select
from src.repository import Repository
from src.lights.model import LightDTO, Operation
from src.pubsub_manager import RedisClient


class LightsRepo(Repository):
    # mongo
    async def save_up(self, light: LightDTO) -> LightDTO | None:
        if light.amount == 0:
            return
        async with self.mongo_client(self.lights_collection) as collection:
            user_lights = await collection.find_one({
                'user_id': light.user_id,
                'chat_id': light.chat_id
            })
            if not user_lights:
                new_light = light.model_dump()
                await collection.insert_one(new_light)
            else:
                ex_light = LightDTO(**user_lights)
                new_light = ex_light + light
                await collection.update_one(
                    {"_id": ObjectId(ex_light.id)},
                    {
                        "$set": {
                            'amount': new_light.amount,
                            'updated_at': new_light.updated_at
                        }
                    }
                )
            return new_light

    # mongo
    async def withdrawn(self, chat_id: int, user_id: int, amount: int = 0):
        async with self.mongo_client(self.lights_collection) as collection:
            user_lights = await collection.find_one({
                'user_id': user_id,
                'chat_id': chat_id
            })
            if not user_lights:
                return
            light = LightDTO(**user_lights)

            if light.amount < amount:
                new_amount = 0
            else:
                new_amount = light.amount - amount

            await collection.update_one(
                {"_id": ObjectId(light.id)},
                {
                    "$set": {
                        'amount': new_amount,
                        'updated_at': datetime.datetime.now()
                    }
                }
            )

    # mongo
    async def calc_amount(self, user_id: int, chat_id: int) -> int:
        async with self.mongo_client(self.lights_collection) as collection:
            user_lights = await collection.find_one({
                'user_id': user_id,
                'chat_id': chat_id
            })
            return LightDTO(**user_lights).amount if user_lights else 0
