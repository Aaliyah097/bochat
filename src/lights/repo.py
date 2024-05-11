from typing import List
from sqlalchemy.sql import select
from src.repository import Repository
from src.lights.table import Lights
from src.lights.model import LightDTO, Operation


class LightsRepo(Repository):
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

    async def override(self, prev_light: LightDTO, light: LightDTO) -> LightDTO:
        prev_light += light
        async with self.session_factory() as session:
            db_model = await session.get(Lights, prev_light.id)
            if db_model:
                db_model.total = prev_light.total
            await session.commit()
            await session.refresh(db_model)
        return self.dto_from_dbo(db_model, LightDTO)

    async def get_prev(self, light: LightDTO, session=None) -> LightDTO | None:
        query = select(Lights).where(
            Lights.chat_id == light.chat_id,
            Lights.user_id == light.user_id
        ).order_by(
            Lights.created_at.desc()
        ).limit(1)
        if session:
            records = await session.execute(query)
            prev_light = records.scalar()
            return self.dto_from_dbo(prev_light, LightDTO) if prev_light else None

        async with self.session_factory() as session:
            records = await session.execute(query)
            prev_light = records.scalar()
            return self.dto_from_dbo(prev_light, LightDTO) if prev_light else None

    async def save_up(self, light: LightDTO) -> LightDTO | None:
        light.operation = Operation.received
        light.acked = True

        async with self.session_factory() as session:
            prev_light = await self.get_prev(light, session)

            if prev_light and light.amount == 0:
                await self.override(prev_light, light)

            if light.amount != 0:
                light.acked = False

            if prev_light:
                light += prev_light

            db_model = Lights(**light.model_dump())

            session.add(db_model)
            await session.commit()
            await session.refresh(db_model)

            if light.amount != 0:
                return self.dto_from_dbo(db_model, LightDTO)

    async def withdrawn(self, light_id: int):
        async with self.session_factory() as session:
            light_dbo = await session.get(Lights, int(light_id))
            prev_light = await self.get_prev(self.dto_from_dbo(light_dbo, LightDTO))

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

    async def calc_amount(self, user_id: int, chat_id: int, session=None) -> int:
        query = select(Lights).where(
            Lights.chat_id == int(chat_id),
            Lights.user_id == int(user_id)
        ).order_by(
            Lights.created_at.desc()
        ).limit(1)
        if session:
            records = await session.execute(query)
            prev_light = records.scalar()
            return prev_light.total if prev_light else 0

        async with self.session_factory() as session:
            records = await session.execute(query)
            prev_light = records.scalar()
            return prev_light.total if prev_light else 0
