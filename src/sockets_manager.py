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

        light = await self.lights_repo.save_up(light.to_dto())

        package = Package(message=message, lights=light)

        return package

    @abstractclassmethod
    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int, layer: int, reply_id: int | None):
        raise NotImplementedError()

    @abstractclassmethod
    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int):
        raise NotImplementedError()


class QueueBroadcater(WebSocketBroadcaster):
    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int, layer: int, reply_id: int | None):
        await self._create_group(chat_id, user_id)
        metrics.ws_connections.inc()

        async for data in websocket.iter_text():
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
            await Monitor.log("Сообщение добавлено в очередь", chat_id, user_id)

            async with RedisClient() as r:
                await r.xadd('notifications', serialized_message)
            await Monitor.log("Уведомление добавлено в очередь", chat_id, user_id)

            metrics.ws_messages.inc()
            metrics.ws_bytes_in.inc(amount=int(len(data)))

        metrics.ws_connections.dec()
        await self.process_queue(websocket, chat_id, layer, user_id, recipient_id)

    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int):
        while True:
            await self._process_queue(websocket, chat_id, layer, user_id, recipient_id)

    async def _process_queue(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int, recipient_id: int):
        stream_name = self.STREAM_NAME % str(chat_id)
        group_name = self.GROUP_NAME % (str(chat_id), str(user_id))
        async with RedisClient() as r:
            events = await r.xreadgroup(group_name, str(user_id), streams={stream_name: '>'})
            # events = await r.xread({self.STREAM_NAME % str(chat_id): '0'})
            if not events:
                return

            for event in events:
                stream, messages = event
                for message_id, message_data in messages:
                    message = Message.deserialize(message_data)
                    start = time.time()
                    try:
                        if int(message.user_id) == int(user_id):
                            message = await self.messages_repo.add_message(
                                message
                            )
                        await Monitor.log("Сообщение сохранено в БД", chat_id, user_id)
                        await r.xack(stream_name, group_name, message_id)
                        # await r.xdel(
                        #     self.STREAM_NAME % str(chat_id),
                        #     message_id)
                        await Monitor.log("Сообщение удалено из очереди", chat_id, user_id)
                    except asyncio.exceptions.CancelledError:
                        await Monitor.log("Задача отменена во время обработки сообщения")
                        break

                    try:
                        package = await self.handle_message(message, layer)
                    except asyncio.exceptions.CancelledError:
                        package = Package(
                            message=message,
                            light=None
                        )
                    await Monitor.log("Сформирован пакет для отправки по вебсокету", chat_id, user_id)

                    # if int(message.user_id) != int(user_id):
                    try:
                        await websocket.send_text(message.model_dump_json())
                    except websockets.exceptions.ConnectionClosedOK:
                        await Monitor.log(
                            "Клиент разорвал соединение")
                    await Monitor.log("Сообщение отправлено по вебсокету", chat_id, user_id)

                    metrics.ws_time_to_process.observe(
                        (time.time() - start) * 1000)


class PubSubBroadcaster(WebSocketBroadcaster):
    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, recipient_id: int, layer: int, reply_id: int | None):
        channel_name = self.CHANNEL_NAME % str(chat_id)

        async for data in websocket.iter_text():
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
                    recipient_id=recipient_id
                )
            except ValidationError:
                continue

            message = await self.messages_repo.add_message(message)

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
                        package = await self.handle_message(message, layer)
                    except asyncio.exceptions.CancelledError:
                        package = Package(
                            message=message,
                            light=None
                        )

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

    if broadcast_backend == 'queue':
        return QueueBroadcater()
    elif broadcast_backend == 'pubsub':
        return PubSubBroadcaster()
