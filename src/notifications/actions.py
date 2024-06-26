from fastapi import APIRouter, Request, Depends
from dependency_injector.wiring import inject, Provide
from src.notifications.device import Device
from container import AppContainer, DeviceRepo


notifications_router = APIRouter(
    prefix='/notifications', tags=['notifications'])


@notifications_router.post("/register-device")
@inject
async def register_device(device: Device,
                          device_repo: DeviceRepo = Depends(Provide[AppContainer.device_repo])):
    await device_repo.store_device(device)


@notifications_router.get("/")
@inject
async def get_user_devices(user_id: int,
                           device_repo: DeviceRepo = Depends(Provide[AppContainer.device_repo])) -> list[Device]:
    return await device_repo.get_user_devices(user_id)
