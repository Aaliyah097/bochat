from src.messages.model import Message
from src.messages.repo import MessagesRepo


class MessagesService:
    def __init__(self):
        self.repo: MessagesRepo = MessagesRepo()

    async def store_new_message(self, message: Message) -> Message:
        return await self.repo.add_message(message)

    async def get_prev_messages(self, message: Message) -> Message | None:
        return await self.repo.get_prev_message(message)
