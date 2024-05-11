import time
import websockets.exceptions
from pydantic import BaseModel
from typing import NoReturn, Any
import asyncio
import logging
from broadcaster import Broadcast
from fastapi import WebSocket
from src import metrics
from src.pubsub_manager import RedisPubSubManager
from src.messages.model import Message
from src.messages.service import MessagesService
from src.messages.repo import MessagesRepo
from src.lights.model import Light, UsersLayer, LightDTO
from src.lights.repo import LightsRepo
from config import settings
from sqlalchemy.orm import sessionmaker
from database import SessionFactory

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
                members = list(self.chats.get(chat_id, {}).values())
                for socket in members:
                    data = message['data'].decode('utf-8')
                    try:
                        await socket.send_text(data)
                    except websockets.exceptions.ConnectionClosedOK as e:
                        pass


class WebSocketBroadcaster:
    broadcast = Broadcast(settings.conn_string)
    messages_repo = MessagesRepo()
    lights_repo = LightsRepo()

    session_factory: sessionmaker = SessionFactory

    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, reply_id: int):
        metrics.ws_connections.inc()

        async for data in websocket.iter_text():
            if len(data) == 0:
                continue
            if data == 'PING':
                await websocket.send_text('PONG')
                continue

            start = time.time()

            message = Message(
                user_id=user_id,
                chat_id=chat_id,
                text=data,
                reply_id=reply_id,
                is_read=False,
                is_edited=False
            )

            await self.broadcast.publish(channel=f"chat_{str(chat_id)}", message=message.model_dump_json())

            metrics.ws_time_to_process.observe((time.time() - start) * 1000)
            metrics.ws_messages.inc()
            metrics.ws_bytes_in.inc(amount=int(len(data)))

        metrics.ws_connections.dec()

    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int):
        async with self.broadcast.subscribe(channel=f"chat_{str(chat_id)}") as subscriber:
            async for event in subscriber:
                message = Message.model_validate_json(event.message)
                if int(message.user_id) != int(user_id):
                    continue

                try:
                    async with self.session_factory() as session:
                        prev_message = await self.messages_repo.get_prev_message(message, session)
                        message = await self.messages_repo.add_message(message, session)
                except asyncio.exceptions.CancelledError:
                    logger.error("Операция отменена по таймауту клиента")
                finally:
                    try:
                        await session.close()
                    except:
                        pass

                time_diff = (message.created_at -
                             prev_message.created_at).total_seconds()
                if time_diff <= 15 and message.user_id != prev_message.user_id:
                    are_both_online = True
                else:
                    are_both_online = False

                light = Light(user_id=message.user_id,
                              chat_id=message.chat_id,
                              message=message,
                              prev_message=prev_message,
                              are_both_online=are_both_online,
                              users_layer=layer)

                try:
                    async with self.session_factory() as session:
                        light = await self.lights_repo.save_up(light.to_dto(), session)
                        package = Package(message=message, lights=light)
                except asyncio.exceptions.CancelledError:
                    logger.error("Операция отменена по таймауту клиента")
                finally:
                    try:
                        await session.close()
                    except:
                        pass

                await websocket.send_text(package.model_dump_json())
