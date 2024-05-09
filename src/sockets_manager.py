import websockets.exceptions
from pydantic import BaseModel
from typing import NoReturn, Any
import asyncio
import logging
from fastapi import WebSocket
from src.pubsub_manager import RedisPubSubManager
from src.messages.model import Message
from src.messages.service import MessagesService
from src.lights.model import Light, UsersLayer, LightDTO
from src.lights.repo import LightsRepo


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


class Package(BaseModel):
    message: Message
    lights: LightDTO | None


class WebSocketManager:
    def __init__(self):
        self.chats: dict[str, dict[str, WebSocket]] = {}
        self.messages_service: MessagesService = MessagesService()
        self.lights_repo: LightsRepo = LightsRepo()
        self.pubsub_clients: dict[str, Any] = {}

    async def add_user_to_chat(self, chat_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()

        if chat_id not in self.chats:
            self.chats[chat_id] = {}
            pubsub_client = RedisPubSubManager()
            self.pubsub_clients[chat_id] = pubsub_client
            pubsub_subscriber = await pubsub_client.subscribe(chat_id)
            asyncio.create_task(self._pubsub_data_reader(
                chat_id, pubsub_subscriber))

        self.chats[chat_id][user_id] = websocket

    async def broadcast_to_chat(self, chat_id: str,
                                message: Message,
                                users_layer: UsersLayer | int = UsersLayer.first):
        members = len(self.chats[chat_id])

        prev_message = await self.messages_service.get_prev_messages(message)
        message = await self.messages_service.store_new_message(message)

        light = Light(user_id=message.user_id,
                      chat_id=message.chat_id,
                      message=message,
                      prev_message=prev_message,
                      are_both_online=members == 2,
                      users_layer=users_layer)

        light = await self.lights_repo.save_up(light.to_dto())
        package = Package(message=message, lights=light)

        await self.pubsub_clients[chat_id].publish(chat_id, package.model_dump_json())

    async def remove_user_from_chat(self, chat_id: str, user_id: str) -> None:
        try:
            del self.chats[chat_id][user_id]
        except (ValueError, KeyError):
            pass

        connections = self.chats.get(chat_id, None)
        if not connections:
            return

        if len(connections) == 0:
            del self.chats[chat_id]
            await self.pubsub_clients[chat_id].unsubscribe(chat_id)

    async def _pubsub_data_reader(self, chat_id: str, pubsub_subscriber) -> NoReturn:
        while True:
            message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
            if message is not None:
                members = self.chats.get(chat_id, {})
                members = members.values()
                for socket in members:
                    data = message['data'].decode('utf-8')
                    try:
                        await socket.send_text(data)
                    except websockets.exceptions.ConnectionClosedOK as e:
                        pass
