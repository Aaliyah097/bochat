from typing import List
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.lights.model import LightDTO
from container import AppContainer, LightsRepo


lights_router = APIRouter(prefix="/lights", tags=['lights'])


@lights_router.post("/{chat_id}/{user_id}/withdrawn/", summary="Списать с пользователя N лайтов", response_model=None)
@inject
async def ack_light(
    chat_id: int,
    user_id: int,
    amount: int = 0,
    lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])
):
    await lights_repo.withdrawn(chat_id, user_id, amount)


@lights_router.get("/{chat_id}/{user_id}", summary="Получить количество лайтов у пользователя в чате", response_model=int)
@inject
async def get_users_lights(chat_id: int, user_id: int,
                           lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])):
    return await lights_repo.calc_amount(user_id, chat_id)
