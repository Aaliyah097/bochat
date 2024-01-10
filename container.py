from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Singleton
from src.messages.repo import MessagesRepo
from src.lights.repo import LightsRepo


class AppContainer(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['src.messages', 'src.lights'])

    messages_repo = Singleton(MessagesRepo)
    lights_repo = Singleton(LightsRepo)
