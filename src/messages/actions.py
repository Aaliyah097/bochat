from typing import Annotated, List
from fastapi import APIRouter, Depends, WebSocket, Query, Body, HTTPException, status
from fastapi.concurrency import run_until_first_complete
from dependency_injector.wiring import inject, Provide

from src.messages.model import Message
from container import AppContainer, MessagesRepo
from src.sockets_manager import get_broadcaster
from src import metrics
from src.auth.auth import auth, auth_ws


chat_router = APIRouter(
    prefix="/messages",
    tags=["messages"],
)


broadcaster = get_broadcaster('pubsub')


@chat_router.post(
    "/last",
    summary="Получить последнее сообщение в каждом чате",
    response_model=dict[int, Message],
)
@inject
async def list_last_messages(
    chats: list[int],
    messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    result = {}
    for chat_id in chats:
        last_message = await messages_repo.get_last_chat_message(chat_id)
        if not last_message:
            continue
        result[chat_id] = last_message
    return result


@chat_router.post(
    "/{chat_id}/{user_id}/mark-read",
    summary="Пометить все сообщения в чате прочитанными для пользователя",
    response_model=None
)
@inject
async def mark_all_read(
    chat_id: int,
    user_id: int,
    messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    await messages_repo.update_has_new_messages(
        user_id,
        chat_id,
        False
    )


@chat_router.get(
    "/{user_id}/new",
    summary='Список чатов, в которых у пользователя есть непрочитанные сообщения',
    response_model=list[int]
)
@inject
async def list_has_user_new_messages_by_chats(
    user_id: int,
    messages_repo: MessagesRepo = Depends(Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    return await messages_repo.list_has_new_messages(user_id)


@chat_router.post("/",
                  deprecated=True,
                  summary="Пометить сообщения прочитанными", response_model=None)
@inject
async def mark_read(messages_ids: list[str],
                    messages_repo: MessagesRepo = Depends(
                        Provide[AppContainer.messages_repo]),
                    _=Depends(auth)
                    ):
    await messages_repo.mark_read(messages_ids)


@chat_router.get("/",
                 summary='Список сообщений конкретного чата',
                 response_model=List[Message])
@inject
async def list_messages(
        chat_id: int,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1)] = 1,
        messages_repo: MessagesRepo = Depends(
            Provide[AppContainer.messages_repo]),
        _=Depends(auth)
):
    return await messages_repo.list_messages(chat_id, page, size)


@chat_router.get("/new",
                 deprecated=True,
                 summary="Список новых сообщений для пользователя в чате", response_model=List[Message])
@inject
async def list_new_messages(
    chat_id: int,
    user_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1)] = 1,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    return await messages_repo.list_new_messages(chat_id, user_id, page, size)


@chat_router.get("/new/count",
                 deprecated=True,
                 summary="Количество новых сообщений для пользователя в чате",
                 response_model=int)
@inject
async def new_nessages_count(
    chat_id: int,
    user_id: int,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    return await messages_repo.count_new_messages_in_chat(chat_id, user_id)


@chat_router.get("/new/by-chats",
                 deprecated=True,
                 summary="Количество новых сообщений для пользователя в каждом чате",
                 response_model=dict[int, int])
@inject
async def count_new_nessages_by_chats(
    user_id: int,
    messages_repo: MessagesRepo = Depends(
        Provide[AppContainer.messages_repo]),
    _=Depends(auth)
):
    return await messages_repo.count_new_messages_by_chats(user_id)


@chat_router.patch("/{message_id}", response_model=None)
@inject
async def edit_message(message_id: str, new_text: Annotated[str, Body()],
                       messages_repo: MessagesRepo = Depends(
                           Provide[AppContainer.messages_repo]),
                       _=Depends(auth)
                       ):
    await messages_repo.edit_message(message_id, new_text)


@chat_router.websocket("/connect")
async def on_message_event_v2(websocket: WebSocket,
                              chat_id: Annotated[int, Query()],
                              user_id: Annotated[int, Query()],
                              recipient_id: Annotated[int, Query()],
                              layer: Annotated[int, Query()],
                              reply_id: Annotated[int | None, Query()] = None,
                              ):
    # await Monitor.log("Пользователь вошел в чат", chat_id, user_id)
    await websocket.accept(
        subprotocol=websocket.headers.get("sec-websocket-protocol")
    )

    if not await auth_ws(websocket.headers.get("sec-websocket-protocol") or ''):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    metrics.ws_connections.inc()

    await run_until_first_complete(
        (broadcaster.chat_ws_receiver, {
            "websocket": websocket,
            "chat_id": chat_id,
            'user_id': user_id,
            'layer': layer,
            'reply_id': reply_id,
            'recipient_id': recipient_id
        }),
        (broadcaster.chat_ws_sender, {
            "websocket": websocket,
            "chat_id": chat_id,
            'layer': layer,
            'user_id': user_id,
            'recipient_id': recipient_id
        }),
    )
    metrics.ws_connections.dec()
    # await Monitor.log("Пользователь вышел из чата", chat_id, user_id)
