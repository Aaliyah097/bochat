from typing import Annotated, List
from fastapi import APIRouter, Depends, WebSocket, Query, WebSocketDisconnect, WebSocketException, Body
from dependency_injector.wiring import inject, Provide
from src.messages.model import Message
from container import AppContainer, MessagesRepo
from src.sockets_manager import WebSocketManager


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
        messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo])
):
    return await messages_repo.list_messages(chat_id, page, size)


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
    try:
        while True:
            data = await websocket.receive_text()
            if len(data) == 0:
                continue
            if data == "PING":
                await websocket.send_text("PONG")
                continue

            message = Message(
                user_id=user_id,
                chat_id=chat_id,
                text=data,
                reply_id=reply_id
            )
            await socket_manager.broadcast_to_chat(chat_id, message, users_layer=layer)
    except (WebSocketDisconnect, WebSocketException):
        await socket_manager.remove_user_from_chat(chat_id, user_id)
