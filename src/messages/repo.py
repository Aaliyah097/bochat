from typing import List
from sqlalchemy.sql import select
from sqlalchemy import desc
from src.messages.model import Message
from src.messages.table import Messages
from src.repository import Repository


class MessagesRepo(Repository):
    async def get_prev_message(self, message: Message) -> Message | None:
        async with self.session_factory() as session:
            query = select(Messages).where(
                Messages.chat_id == message.chat_id
            ).order_by(
                Messages.created_at.desc()
            ).limit(1)

            records = await session.execute(query)
            message = records.scalar()
            if not message:
                return None

            return self.dto_from_dbo(message, Message)

    async def add_message(self, message: Message) -> Message:
        db_model = Messages(**message.model_dump())
        async with self.session_factory() as session:
            session.add(db_model)
            await session.commit()
            await session.refresh(db_model)
        return self.dto_from_dbo(db_model, Message)

    async def edit_message(self, message_id: int, new_text: str) -> Message:
        async with self.session_factory() as session:
            message = await session.get(Messages, message_id)
            if not message:
                raise Exception("Сообщение не найдено")
            message.text = new_text
            await session.commit()
            await session.refresh(message)
            return self.dto_from_dbo(message, Message)

    async def list_messages(self, chat_id: int, page: int = 1, size: int = 50) -> List[Message]:
        offset = (page - 1) * size
        async with self.session_factory() as session:
            query = (
                select(Messages)
                .filter(Messages.chat_id == chat_id)
                .order_by(desc(Messages.created_at))
                .offset(offset).limit(size)
            )
            records = await session.execute(query)
            return [self.dto_from_dbo(message, Message) for message in records.scalars().all()]
