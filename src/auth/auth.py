from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from src.auth.repo import AuthRepo


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def auth(token: Annotated[str, Depends(oauth2_scheme)]):
    if not await AuthRepo.verify(token):
        raise HTTPException(status_code=401)


async def auth_ws(token: str) -> bool:
    return await AuthRepo.verify(token)
