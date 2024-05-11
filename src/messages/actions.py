import time
from typing import Annotated, List
from fastapi import APIRouter, Depends, WebSocket, Query, WebSocketDisconnect, WebSocketException, Body
from fastapi.concurrency import run_until_first_complete
from dependency_injector.wiring import inject, Provide

from src.messages.model import Message
from container import AppContainer, MessagesRepo
from src.sockets_manager import WebSocketManager, WebSocketBroadcaster
from src import metrics


chat_router = APIRouter(prefix="/messages", tags=["messages"])

socket_manager: WebSocketManager = WebSocketManager()


@chat_router.post("/",
                  summary="Пометить сообщения прочитанными")
@inject
async def mark_read(messages_ids: list[int],
                    messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo])):
    return await messages_repo.mark_read(messages_ids)


@chat_router.get("/",
                 summary='Список сообщений конкретного чата',
                 response_model=List[Message])
@inject
async def list_messages(
        chat_id: int,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1)] = 15,
        messages_repo: MessagesRepo = Depends(
            Provide[AppContainer.messages_repo])
):
    return await messages_repo.list_messages(chat_id, page, size)


@chat_router.get("/new", summary="Список новых сообщений для пользователя в чате", response_model=List[Message])
@inject
async def list_new_messages(
    chat_id: int,
    user_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1)] = 15,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo])
):
    return await messages_repo.list_new_messages(chat_id, user_id, page, size)


@chat_router.get("/new/count",
                 summary="Количество новых сообщений для пользователя в чате",
                 response_model=int)
@inject
async def new_nessages_count(
    chat_id: int,
    user_id: int,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo])
):
    return await messages_repo.count_new_messages_in_chat(chat_id, user_id)


@chat_router.get("/new/by-chats",
                 summary="Количество новых сообщений для пользователя в каждом чате",
                 response_model=dict[int, int])
@inject
async def count_new_nessages_by_chats(
    user_id: int,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo])
):
    return await messages_repo.count_new_messages_by_chats(user_id)


@chat_router.patch("/{message_id}", response_model=Message)
@inject
async def edit_message(message_id: int, new_text: Annotated[str, Body()],
                       messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo])):
    return await messages_repo.edit_message(message_id, new_text)


@chat_router.websocket("/connect")
async def on_message_event(websocket: WebSocket,
                           chat_id: Annotated[str, Query()],
                           user_id: Annotated[str, Query()],
                           layer: Annotated[int, Query()],
                           reply_id: Annotated[int | None, Query()] = None
                           ):
    await socket_manager.add_user_to_chat(chat_id, user_id, websocket)
    # событие входа в чат
    metrics.ws_connections.inc()
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) == 0:
                continue
            if data == "PING":
                await websocket.send_text("PONG")
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
            await socket_manager.broadcast_to_chat(chat_id, message, users_layer=layer)
            # Событие рассылки сообщений
            metrics.ws_time_to_process.observe((time.time() - start) * 1000)
            metrics.ws_messages.inc()
    except (WebSocketDisconnect, WebSocketException):
        await socket_manager.remove_user_from_chat(chat_id, user_id)
        # событие выхода из чата
        metrics.ws_connections.dec()


@chat_router.websocket("/v2/connect")
async def on_message_event_v2(websocket: WebSocket,
                              chat_id: Annotated[str, Query()],
                              user_id: Annotated[str, Query()],
                              layer: Annotated[int, Query()],
                              reply_id: Annotated[int | None, Query()] = None
                              ):
    await websocket.accept()
    broadcaster = WebSocketBroadcaster()

    await run_until_first_complete(
        (broadcaster.chat_ws_receiver, {
         "websocket": websocket, "chat_id": chat_id, 'user_id': user_id, 'reply_id': reply_id}),
        (broadcaster.chat_ws_sender, {
         "websocket": websocket, "chat_id": chat_id, 'layer': layer}),
    )
