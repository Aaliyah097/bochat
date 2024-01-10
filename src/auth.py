from httpx import AsyncClient
from typing import Annotated
from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from config import settings
from src.messages.model import Message


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

auth_router = APIRouter(prefix="/auth", tags=['auth'])


@auth_router.post("/token")
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    async with AsyncClient(base_url=settings.auth_uri, verify=False) as client:
        response = await client.post(
            url="/",
            json={
                "login": form_data.username,
                "password": form_data.password
            },
            headers={
                "Content-Type": "application/json"
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Неправильные учетные даныне")

        result = response.json()
        return {
            "access_token": result['access'],
            "type": "Bearer"
        }


def auth(token: Annotated[str, Depends(oauth2_scheme)]) -> int:
    try:
        decode = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
        return decode.get("user_id", None)
    except jwt.exceptions.PyJWTError:
        raise HTTPException(status_code=403, detail="Неверный токен")


def has_message(user_id: int, message: Message) -> bool:
    return user_id == message.user_id
