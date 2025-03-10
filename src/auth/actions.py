from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.auth.model import Tokens
from src.auth.repo import AuthRepo


auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post('/login', response_model=Tokens)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    access, refresh = await AuthRepo.login(
        form_data.username,
        password=form_data.password
    )
    return Tokens(
        access_token=access,
        refresh_token=refresh
    )
