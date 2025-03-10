from fastapi import APIRouter, Depends, Body
from dependency_injector.wiring import inject, Provide
from container import AppContainer, LightsRepo
from src.auth.auth import auth


lights_router = APIRouter(
    prefix="/lights",
    tags=['lights'],
    dependencies=[Depends(auth)]
)


@lights_router.post("/{chat_id}/{user_id}/withdrawn/", summary="Списать с пользователя N лайтов", response_model=None)
@inject
async def ack_light(
    chat_id: int,
    user_id: int,
    amount: int = Body(..., embed=True, gt=0),
    lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])
):
    await lights_repo.withdrawn(chat_id, user_id, amount)


@lights_router.get("/{chat_id}/{user_id}", summary="Получить количество лайтов у пользователя в чате", response_model=int)
@inject
async def get_users_lights(chat_id: int, user_id: int,
                           lights_repo: LightsRepo = Depends(Provide[AppContainer.lights_repo])):
    return await lights_repo.calc_amount(user_id, chat_id)
