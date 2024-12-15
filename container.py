from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from dependency_injector.providers import Singleton
from src.messages.repo import MessagesRepo
from src.lights.repo import LightsRepo
from src.notifications.repo import DeviceRepo
from src.onboarding.repo import OnboardingRepo
from src.onboarding.service import OnboardingService


class AppContainer(DeclarativeContainer):
    wiring_config = WiringConfiguration(
        packages=['src.messages', 'src.lights', 'src.notifications', 'src.onboarding'])

    messages_repo = Singleton(MessagesRepo)
    lights_repo = Singleton(LightsRepo)
    device_repo = Singleton(DeviceRepo)
    onboarding_repo = Singleton(OnboardingRepo)
    onboarding_service = Singleton(OnboardingService)
