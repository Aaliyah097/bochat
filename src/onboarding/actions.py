from fastapi import APIRouter, Depends
from .models import Action, Onboarding, UserAction, NextAction
from dependency_injector.wiring import inject, Provide
from container import AppContainer, OnboardingService


onboarding_router = APIRouter(prefix="/onboarding", tags=['onboarding'])


@onboarding_router.post(
    "/action",
    summary="Сохранить пользовательское действие во время онбординга",
    response_model=NextAction
)
@inject
async def save_message_from_user(
    user_action: UserAction,
    onboarding_service: OnboardingService = Depends(
        Provide[AppContainer.onboarding_service])
):
    return await onboarding_service.handle_user_action(user_action)


@onboarding_router.get(
    "/",
    summary="Получить сообщения пользователя в чате онбординга",
    response_model=Onboarding
)
@inject
async def get_user_onboarding_chat(
    user_id: int,
    onboarding_service: OnboardingService = Depends(
        Provide[AppContainer.onboarding_service])
):
    return await onboarding_service.get_onboarding(user_id)
