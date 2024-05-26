import redis
from pydantic import ValidationError
import time
import websockets.exceptions
from pydantic import BaseModel
from typing import NoReturn, Any, Union
import asyncio
import logging
from fastapi import WebSocket
from src import metrics
from src.pubsub_manager import RedisClient
from src.messages.model import Message
from src.messages.service import MessagesService
from src.messages.repo import MessagesRepo
from src.lights.model import Light, UsersLayer, LightDTO
from src.lights.repo import LightsRepo
from config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import InterfaceError
from logger import logger


class Package(BaseModel):
    message: Message
    lights: LightDTO | None


class WebSocketBroadcaster:
    messages_repo = MessagesRepo()
    lights_repo = LightsRepo()

    STREAM_NAME = 'channel_%s_messages'
    MAX_STREAM_LEN = 100

    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int, reply_id: int | None):
        if not user_id or not chat_id:
            return

        try:
            user_id = int(user_id)
            chat_id = int(chat_id)
        except ValueError:
            return

        if not isinstance(reply_id, int) and not reply_id is None:
            reply_id = None

        if not isinstance(websocket, WebSocket):
            return

        metrics.ws_connections.inc()

        async for data in websocket.iter_text():
            if len(data) == 0:
                continue
            if data == 'PING':
                try:
                    await websocket.send_text('PONG')
                except websockets.exceptions.ConnectionClosedOK:
                    logger.warning("Клиент разорвал соединение")
                continue

            try:
                message = Message(
                    user_id=user_id,
                    chat_id=chat_id,
                    text=data,
                    reply_id=reply_id,
                    is_read=False,
                    is_edited=False,
                    recipient_id=recipient_id
                )
            except ValidationError:
                continue

            serialized_message = message.serialize()

            async with RedisClient() as r:
                await r.xadd(
                    self.STREAM_NAME % str(chat_id),
                    serialized_message,
                    maxlen=self.MAX_STREAM_LEN
                )

            async with RedisClient() as r:
                await r.xadd('notifications', serialized_message)

            metrics.ws_messages.inc()
            metrics.ws_bytes_in.inc(amount=int(len(data)))

        metrics.ws_connections.dec()

    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int,):
        if not layer:
            layer = 1

        if not chat_id or not user_id or not recipient_id:
            return

        try:
            chat_id = int(chat_id)
            user_id = int(user_id)
            recipient_id = int(recipient_id)
        except ValueError:
            return

        if not isinstance(websocket, WebSocket):
            return

        async with RedisClient() as r:
            while websocket.client_state != 2:  # 2=disconnected
                events = await r.xread({self.STREAM_NAME % str(chat_id): '0'})
                if not events:
                    continue

                for event in events:
                    stream, messages = event
                    for message_id, message_data in messages:
                        message = Message.deserialize(message_data)
                        if int(user_id) == int(message.user_id):
                            continue

                        start = time.time()
                        try:
                            message = await self.messages_repo.add_message(
                                message
                            )
                        except asyncio.exceptions.CancelledError:
                            break

                        try:
                            package = await self.handle_message(message, layer)
                        except asyncio.exceptions.CancelledError:
                            package = Package(
                                message=message,
                                light=None
                            )

                        await r.xdel(
                            self.STREAM_NAME % str(chat_id),
                            message_id)

                        try:
                            await websocket.send_text(message.model_dump_json())
                        except websockets.exceptions.ConnectionClosedOK:
                            logger.warning("Клиент разорвал соединение")

                        metrics.ws_time_to_process.observe(
                            (time.time() - start) * 1000)

    async def handle_message(self, message: Message, layer: int) -> Package:
        prev_message = await self.messages_repo.get_last_chat_message(message.chat_id)

        if not prev_message:
            prev_message = message
        await self.messages_repo.store_last_chat_message(message.chat_id, message)

        if message and message.created_at and prev_message and prev_message.created_at:
            time_diff = (message.created_at -
                         prev_message.created_at).total_seconds()
        else:
            time_diff = 0

        if not message or not message.user_id or not prev_message or not prev_message.user_id:
            are_both_online = False
        elif time_diff <= 15 and message.user_id != prev_message.user_id:
            are_both_online = True
        else:
            are_both_online = False

        light = Light(user_id=message.user_id,
                      chat_id=message.chat_id,
                      message=message,
                      prev_message=prev_message,
                      are_both_online=are_both_online,
                      users_layer=layer)

        light = await self.lights_repo.save_up(light.to_dto())

        package = Package(message=message, lights=light)

        return package
