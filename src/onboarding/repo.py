from src.repository import Repository
from .models import (
    UserAction,
    Onboarding,
    BlockMessage,
    AssistantMessage,
    BlockMessage,
    Action,
    OnboardingMessage
)
from src.pubsub_manager import RedisClient


class OnboardingRepo(Repository):
    assistant_messages_key = "asisstant_messages"

    async def save_action(self, action: UserAction) -> UserAction:
        async with self.mongo_client(self.onboardings_collection) as collection:
            await collection.insert_one(
                action.model_dump()
            )
            return action

    async def get_user_actions(self, user_id: int, action: Action | None = None) -> UserAction:
        params = {
            'u_id': user_id,
        }
        if action:
            params['action'] = action

        async with self.mongo_client(self.onboardings_collection) as collection:
            cursor = collection.find(
                params
            ).sort([('created_at', 1), ])
            return [
                UserAction(**action)
                for action in await cursor.to_list(None)
            ]

    async def get_user_messages(self, user_id: int) -> list[OnboardingMessage]:
        async with self.mongo_client(self.onboardings_collection) as collection:
            cursor = collection.find(
                {
                    'u_id': user_id,
                    'message': {'$ne': None}
                }
            ).sort([('created_at', 1), ])
            user_messages = [
                OnboardingMessage(**action['message'])
                for action in await cursor.to_list(None)
            ]
            return user_messages

    async def get_chat_history(self, user_id: int) -> list[BlockMessage]:
        user_actions = await self.get_user_actions(user_id)
        assistant_messages = await self.get_assistant_message()

        chat: list[BlockMessage] = []
        last_block: int = 0

        for assist_message in assistant_messages:
            if assist_message.block_id != last_block:
                try:
                    user_action = user_actions[last_block]
                except IndexError:
                    break
                if user_action.message:
                    chat.append(BlockMessage(
                        message=user_action.message, from_user=True))
                last_block += 1
            chat.append(BlockMessage(message=assist_message, from_user=False))

        return chat

    async def get_assistant_message(self, block_id: int | None = None) -> list[AssistantMessage]:
        a_msgs, messages = [], []

        async with RedisClient() as client:
            messages = await client.lrange(self.assistant_messages_key, 0, -1)

        for message in messages:
            a_msg = AssistantMessage.parse_raw(message.decode('utf-8'))
            if block_id is not None and str(a_msg.block_id) != str(block_id):
                continue
            a_msgs.append(a_msg)

        return a_msgs

    async def override_assistant_messages(self, new_messages: list[AssistantMessage]) -> None:
        async with RedisClient() as client:
            await client.delete(self.assistant_messages_key)
            for new_message in new_messages:
                await client.rpush(
                    self.assistant_messages_key,
                    new_message.model_dump_json()
                )
