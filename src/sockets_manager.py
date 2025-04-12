import datetime
import json
from abc import ABC, abstractclassmethod
from collections import defaultdict
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
from monitor import Monitor


class Package(BaseModel):
    message: Message
    lights: LightDTO | None
    reply_message: Message | None = None


class WebSocketBroadcaster(ABC):
    messages_repo = MessagesRepo()
    lights_repo = LightsRepo()

    STREAM_NAME = 'channel_%s_messages'
    MAX_STREAM_LEN = 100
    GROUP_NAME = 'channel_%s_user_%s_group'
    CHANNEL_NAME = 'channel_%s'
    NOTIFICATIONS_STREAM = 'notifications'

    async def _create_group(self, chat_id: int, user_id):
        async with RedisClient() as r:
            try:
                await r.xgroup_create(self.STREAM_NAME % str(chat_id), self.GROUP_NAME % (str(chat_id), str(user_id)), id='$', mkstream=True)
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP Consumer Group name already exists" in str(e):
                    pass

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

        await self.lights_repo.save_up(light.to_dto())

        package = Package(
            message=message,
            lights=light.to_dto() if light.amount else None
        )

        return package

    @abstractclassmethod
    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int, layer: int, reply_id: int | None):
        raise NotImplementedError()

    @abstractclassmethod
    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int):
        raise NotImplementedError()


class PubSubBroadcaster(WebSocketBroadcaster):
    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int):
        channel_name = self.CHANNEL_NAME % str(chat_id)

        async for data in websocket.iter_text():
            try:
                encoded_data = json.loads(data)
                data, sent_at, reply_id = encoded_data.get(
                    'message', ""), encoded_data.get('sent_at'), encoded_data.get('reply_id')
            except (json.JSONDecodeError, ValueError):
                sent_at = None
                reply_id = None

            if len(data) == 0:
                continue
            if data == 'PING':
                try:
                    await websocket.send_text('PONG')
                except websockets.exceptions.ConnectionClosedOK:
                    await Monitor.log("Клиент разорвал соединение")
                continue

            try:
                message = Message(
                    user_id=user_id,
                    chat_id=chat_id,
                    text=data,
                    reply_id=reply_id,
                    is_read=False,
                    is_edited=False,
                    recipient_id=recipient_id,
                    sent_at=sent_at
                )
            except ValidationError:
                continue

            message = await self.messages_repo.add_message(message)
            await self.messages_repo.update_has_new_messages(
                recipient_id,
                chat_id,
                True
            )

            async with RedisClient() as r:
                await r.publish(channel_name, message.json_dumps())
                await r.xadd(self.NOTIFICATIONS_STREAM, message.serialize())

            metrics.ws_messages.inc()
            metrics.ws_bytes_in.inc(amount=int(len(data)))

    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int):
        channel_name = self.CHANNEL_NAME % str(chat_id)

        async with RedisClient() as r:
            pubsub = r.pubsub()
            await pubsub.subscribe(channel_name)
            try:
                async for message in pubsub.listen():
                    start = time.time()

                    if message["type"] != "message":
                        continue

                    message = Message.json_loads(message['data'])

                    try:
                        if int(user_id) != int(message.user_id):
                            package = Package(
                                message=message,
                                lights=None
                            )
                        else:
                            package = await self.handle_message(message, layer)
                    except asyncio.exceptions.CancelledError as e:
                        package = Package(
                            message=message,
                            lights=None
                        )

                    if package.message.reply_id:
                        package.reply_message = await self.messages_repo.get_message_by_id(package.message.reply_id)

                    try:
                        await websocket.send_text(package.model_dump_json())
                    except websockets.exceptions.ConnectionClosedOK:
                        await Monitor.log(
                            "Клиент разорвал соединение")

                    metrics.ws_time_to_process.observe(
                        (time.time() - start) * 1000)
            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()


def get_broadcaster(broadcast_backend: str) -> WebSocketBroadcaster:
    if not broadcast_backend:
        raise ValueError("Не определен бэкенд брокастера")

    elif broadcast_backend == 'pubsub':
        return PubSubBroadcaster()
    else:
        return PubSubBroadcaster()
