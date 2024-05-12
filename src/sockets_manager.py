from pydantic import ValidationError
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
from sqlalchemy.exc import InterfaceError
from database import SessionFactory
from logger import logger


class Package(BaseModel):
    message: Message
    lights: LightDTO | None


class WebSocketBroadcaster:
    broadcast = Broadcast(settings.conn_string)
    messages_repo = MessagesRepo()
    lights_repo = LightsRepo()

    session_factory: sessionmaker = SessionFactory

    async def chat_ws_receiver(self, websocket: WebSocket, chat_id: int, user_id: int, reply_id: int | None):
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
                    return
                continue
            try:
                await websocket.send_text("OK")
            except websockets.exceptions.ConnectionClosedOK:
                logger.warning("Клиент разорвал соединение")
                return

            try:
                message = Message(
                    user_id=user_id,
                    chat_id=chat_id,
                    text=data,
                    reply_id=reply_id,
                    is_read=False,
                    is_edited=False
                )
            except ValidationError:
                continue

            await self.broadcast.publish(channel=f"chat_{str(chat_id)}", message=message.model_dump_json())

            metrics.ws_messages.inc()
            metrics.ws_bytes_in.inc(amount=int(len(data)))

        metrics.ws_connections.dec()

    async def chat_ws_sender(self, websocket: WebSocket, chat_id: int, layer: int, user_id: int):
        if not layer:
            layer = 1

        if not chat_id or not user_id:
            return

        try:
            chat_id = int(chat_id)
            user_id = int(user_id)
        except ValueError:
            return

        if not isinstance(websocket, WebSocket):
            return

        async with self.broadcast.subscribe(channel=f"chat_{str(chat_id)}") as subscriber:
            async for event in subscriber:
                start = time.time()

                try:
                    message = Message.model_validate_json(event.message)
                except ValidationError:
                    continue

                prev_message = await self.messages_repo.get_last_chat_message(chat_id)

                try:
                    message = await self.messages_repo.add_message(message)
                    if not prev_message:
                        prev_message = message
                    await self.messages_repo.store_last_chat_message(chat_id, message)
                except asyncio.exceptions.CancelledError as e:
                    logger.warning("Операция отменена по таймауту клиента")
                    return

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

                try:
                    light = await self.lights_repo.save_up(light.to_dto())
                except asyncio.exceptions.CancelledError:
                    logger.warning("Операция отменена по таймауту клиента")
                    return

                package = Package(message=message, lights=light)

                if int(message.user_id) != int(user_id):
                    try:
                        await websocket.send_text(package.model_dump_json())
                    except websockets.exceptions.ConnectionClosedOK:
                        logger.warning("Клиент разорвал соединение")

                metrics.ws_time_to_process.observe(
                    (time.time() - start) * 1000)
