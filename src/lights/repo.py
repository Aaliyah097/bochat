from typing import List, Union
import json
from sqlalchemy.sql import select
from src.repository import Repository
from src.lights.table import Lights
from src.lights.model import LightDTO, Operation
from src.pubsub_manager import RedisClient


class LightsRepo(Repository):
    async def get_last_user_light(self, user_id: int, chat_id: int) -> Union[LightDTO, None]:
        async with RedisClient() as client:
            res = await client.get(f"last_light_{user_id}_{chat_id}")
            return LightDTO.model_validate_json(res.decode("utf-8")) if res else None

    async def store_last_user_light(self, user_id: int, chat_id: int, light: LightDTO):
        async with RedisClient() as client:
            await client.set(f"last_light_{user_id}_{chat_id}", light.model_dump_json())

    async def get_free(self, chat_id: int, user_id: int) -> List[LightDTO]:
        async with self.session_factory() as session:
            query = select(Lights).where(
                Lights.chat_id == chat_id,
                Lights.user_id == user_id,
                Lights.acked == False
            )
            records = await session.execute(query)
            messages = records.scalars()
            return [self.dto_from_dbo(message, LightDTO) for message in messages]

    async def override(self, prev_light: LightDTO, light: LightDTO, session) -> LightDTO:
        db_model = await session.get(Lights, prev_light.id)
        if db_model:
            prev_light += light
            db_model.total = prev_light.total

    async def get_prev(self, light: LightDTO, session) -> LightDTO | None:
        query = select(Lights).where(
            Lights.chat_id == light.chat_id,
            Lights.user_id == light.user_id
        ).order_by(
            Lights.created_at.desc()
        ).limit(1)

        records = await session.execute(query)
        prev_light = records.scalar()
        return self.dto_from_dbo(prev_light, LightDTO) if prev_light else None

    async def save_up(self, light: LightDTO, session) -> LightDTO | None:
        light.operation = Operation.received
        light.acked = True

        prev_light = await self.get_last_user_light(light.user_id, light.chat_id)

        if prev_light and light.amount == 0:
            await self.override(prev_light, light, session)

        if light.amount != 0:
            light.acked = False

        if prev_light:
            light += prev_light

        db_model = Lights(**light.model_dump())
        session.add(db_model)
        await session.commit()
        await session.refresh(db_model)

        await self.store_last_user_light(light.user_id, light.chat_id, self.dto_from_dbo(db_model, LightDTO))

        if light.amount != 0:
            return self.dto_from_dbo(db_model, LightDTO)

    async def withdrawn(self, light_id: int):
        async with self.session_factory() as session:
            light_dbo = await session.get(Lights, int(light_id))
            prev_light = await self.get_last_user_light(light_dbo.user_id, light_dbo.chat_id)

            if prev_light.total < light_dbo.amount:
                raise Exception("Недостаточно лайтов")

            light_dbo.acked = True

            new_light = Lights(
                user_id=light_dbo.user_id,
                chat_id=light_dbo.chat_id,
                amount=light_dbo.amount,
                total=prev_light.total - light_dbo.amount,
                operation=Operation.withdrawn,
                acked=True
            )
            session.add(new_light)

            await session.commit()

    async def calc_amount(self, user_id: int, chat_id: int) -> int:
        async with self.session_factory() as session:
            query = select(Lights).where(
                Lights.chat_id == int(chat_id),
                Lights.user_id == int(user_id)
            ).order_by(
                Lights.created_at.desc()
            ).limit(1)

            records = await session.execute(query)
            prev_light = records.scalar()
            return prev_light.total if prev_light else 0
