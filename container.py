from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Factory
from src.messages.repo import MessagesRepo
from src.lights.repo import LightsRepo
from src.notifications.repo import DeviceRepo


class AppContainer(DeclarativeContainer):
    wiring_config = WiringConfiguration(
        packages=['src.messages', 'src.lights', 'src.notifications'])

    messages_repo = Factory(MessagesRepo)
    lights_repo = Factory(LightsRepo)
    device_repo = Factory(DeviceRepo)
