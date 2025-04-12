from typing import Union
from bson import ObjectId
from bson.errors import InvalidId
import json
import datetime
import pytz
from typing import List
from sqlalchemy.sql import select, update, text
from sqlalchemy import desc, func
from src.messages.model import Message, MessagePackage
from src.repository import Repository
from src.pubsub_manager import RedisClient


class MessagesRepo(Repository):
    has_new_messages_key = "has_mew_msgs_"
    has_new_messages_key_delimeter = ":"
    last_message_key = "last_message_"

    async def list_has_new_messages(self, user_id: int) -> list[int]:
        try:
            user_id = int(user_id)
        except ValueError:
            return []

        async with RedisClient() as client:
            keys = await client.keys(pattern=f'{self.has_new_messages_key}{str(user_id)}{self.has_new_messages_key_delimeter}*')
            return [
                int(key.decode(
                    'utf-8').split(self.has_new_messages_key_delimeter)[1])
                for key in keys
            ]

    async def update_has_new_messages(
        self, user_id: int, chat_id: int, new_state: bool
    ):
        try:
            user_id = int(user_id)
            chat_id = int(chat_id)
        except ValueError:
            return

        if not isinstance(new_state, bool):
            return

        key = f"{self.has_new_messages_key}{str(user_id)}{self.has_new_messages_key_delimeter}{str(chat_id)}"

        async with RedisClient() as client:
            if new_state:
                await client.setnx(key, 1)
            else:
                await client.delete(key)

    async def session(self):
        pass

    # redis
    async def store_last_chat_message(self, chat_id: int, message: Message):
        if not chat_id or not message:
            return

        if not isinstance(message, Message):
            return

        chat_id = str(chat_id)

        async with RedisClient() as client:
            await client.set(f"{self.last_message_key}{chat_id}", message.model_dump_json())

    # redis
    async def get_last_chat_message(self, chat_id: int) -> Union[Message, None]:
        if not chat_id:
            return

        chat_id = str(chat_id)

        async with RedisClient() as client:
            res = await client.get(f"{self.last_message_key}{chat_id}")
            return Message.model_validate_json(res.decode("utf-8")) if res else None

    # mongo
    async def add_message(self, message: Message) -> Union[Message, None]:
        if not message:
            return

        if not isinstance(message, Message):
            return

        message.created_at = self.get_now()
        if not message.sent_at:
            message.sent_at = message.created_at

        dumped_messsage = message.model_dump()
        if message.reply_id:
            try:
                dumped_messsage['reply_id'] = ObjectId(str(message.reply_id))
            except InvalidId:
                dumped_messsage['reply_id'] = None

        async with self.mongo_client(self.messages_collection) as collection:
            result = await collection.insert_one(dumped_messsage)
            message.id = str(result.inserted_id)

        return message

    # mongo
    async def get_message_by_id(self, message_id: str) -> Union[Message, None]:
        if not message_id:
            return

        try:
            message_id = ObjectId(str(message_id))
        except InvalidId:
            return None

        async with self.mongo_client(self.messages_collection) as collection:
            message = await collection.find_one({"_id": message_id})

        return Message(**message) if message else None

    # mongo
    async def edit_message(self, message_id: str, new_text: str) -> Union[Message, None]:
        if not message_id:
            return

        if not new_text:
            new_text = ''

        message_id = str(message_id)

        async with self.mongo_client(self.messages_collection) as collection:
            await collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {'text': new_text}}
            )

    # mongo
    async def mark_read(self, messages_ids: list[str]) -> None:
        if not isinstance(messages_ids, list):
            return

        async with self.mongo_client(self.messages_collection) as collection:
            records = await collection.update_many(
                {"_id": {"$in": [ObjectId(str(m_id))
                                 for m_id in messages_ids]}},
                {"$set": {"is_read": True}}
            )

    # mongo
    async def list_messages(self, chat_id: int, page: int = 1, size: int = 1) -> List[MessagePackage]:
        if not chat_id:
            return []

        try:
            chat_id = int(chat_id)
        except ValueError:
            return []

        if not page:
            page = 1
        if not size:
            size = 1

        try:
            page = int(page)
        except ValueError:
            page = 1

        try:
            size = int(size)
        except ValueError:
            size = 1

        offset = (page - 1) * size

        async with self.mongo_client(self.messages_collection) as collection:
            cursor = collection.aggregate([
                {"$match": {"chat_id": chat_id}},
                {"$sort": {"created_at": -1}},
                {"$skip": offset},
                {"$limit": size},
                {
                    "$lookup": {
                        "from": "messages",              # Название коллекции
                        "localField": "reply_id",     # Поле в текущем документе
                        "foreignField": "_id",           # Поле в документе, на который ссылаемся
                        "as": "reply_to"                 # Как назвать вложенный результат
                    }
                },
                {
                    "$unwind": {
                        "path": "$reply_to",
                        "preserveNullAndEmptyArrays": True  # Чтобы оставить документы без вложений
                    }
                }
            ])

        result_messages = []
        for result_message in await cursor.to_list(length=size):
            if 'reply_to' in result_message:
                reply_to = result_message.pop('reply_to')
            else:
                reply_to = None
            result_messages.append(
                MessagePackage(
                    message=Message(**result_message),
                    reply_to=Message(**reply_to) if reply_to else None
                )
            )

        return result_messages

    # mongo
    async def list_new_messages(self, chat_id: int, user_id: int, page: int = 1, size: int = 1) -> List[Message]:
        # deprecated
        if not chat_id or not user_id:
            return []

        try:
            chat_id = int(chat_id)
            user_id = int(user_id)
        except ValueError:
            return []

        if not page:
            page = 1
        if not size:
            size = 1

        try:
            page = int(page)
        except ValueError:
            page = 1

        try:
            size = int(size)
        except ValueError:
            size = 1

        offset = (page - 1) * size

        async with self.mongo_client(self.messages_collection) as collection:
            cursor = collection.find({
                'chat_id': chat_id,
                'user_id': {"$ne": user_id},
                'is_read': False
            }).sort("created_at", -1).skip(offset).limit(size)

            return [Message(**doc) for doc in await cursor.to_list(length=size)]

    # mongo
    async def count_new_messages_in_chat(self, chat_id: int, user_id: int) -> int:
        if not chat_id or not user_id:
            return 0

        try:
            chat_id = int(chat_id)
            user_id = int(user_id)
        except ValueError:
            return 0

        async with self.mongo_client(self.messages_collection) as collection:
            return await collection.count_documents({
                'chat_id': chat_id,
                'user_id': {"$ne": user_id},
                'is_read': False
            })

    # mongo
    async def count_new_messages_by_chats(self, user_id: int) -> dict:
        if not user_id:
            return {}

        try:
            user_id = int(user_id)
        except ValueError:
            return {}

        result = {}
        async with self.mongo_client(self.messages_collection) as collection:
            pipeline = [
                {"$match": {"user_id": {"$ne": user_id}, "is_read": False}},
                {"$group": {"_id": "$chat_id", "count": {"$sum": 1}}}
            ]

            res = await collection.aggregate(pipeline).to_list(None)
            for r in res:
                result[r['_id']] = r['count']

        return result
