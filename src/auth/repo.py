from httpx import AsyncClient
from config import settings
from src.pubsub_manager import RedisClient
import jwt
from datetime import datetime


class AuthRepo:
    @staticmethod
    async def login(username: str, password: str) -> tuple[str, str]:
        async with AsyncClient(
            base_url=settings.create_token_uri
        ) as session:
            response = await session.post(
                '/',
                data={
                    'login_tg': username,
                    'password': password
                }
            )
            if not response.status_code == 200:
                response.raise_for_status()

            data = response.json()
            return (
                data['access'],
                data['refresh']
            )

    @staticmethod
    async def verify(token: str) -> bool:
        async with RedisClient() as session:
            ex = await session.get(token)
            if ex:
                return True

        async with AsyncClient(
            base_url=settings.verify_token_uri
        ) as session:
            response = await session.post(
                '/',
                data={
                    'token': token
                }
            )
            if response.status_code != 200:
                return False

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload['exp'])
        ttl = (exp - datetime.now()).seconds

        async with RedisClient() as session:
            await session.set(token, 1)
            await session.expire(token, ttl)

        return True
