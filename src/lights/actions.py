from typing import List
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.lights.model import LightDTO
from container import AppContainer, LightsRepo


lights_router = APIRouter(prefix="/lights", tags=['lights'])


@lights_router.get("/",
                   summary="Получить записи по лайтам, которые не выданы пользователю",
                   response_model=List[LightDTO])
@inject
async def get_free_lights(chat_id: int, user_id: int,
                          lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])):
    return await lights_repo.get_free(chat_id, user_id)


@lights_router.get("/{light_id}", summary="Начислить пользователю лайты")
@inject
async def ack_light(light_id, lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])):
    await lights_repo.withdrawn(light_id)


@lights_router.get("/{chat_id}/{user_id}", summary="Получить количество лайтов у пользователя в чате")
@inject
async def get_users_lights(chat_id: int, user_id: int,
                           lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])):
    return await lights_repo.calc_amount(user_id, chat_id)
