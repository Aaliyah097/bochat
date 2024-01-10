from typing import Annotated
from dependency_injector.wiring import inject
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.messages import chat_router
from src.lights.actions import lights_router
from src.auth import auth_router
from container import AppContainer
from database import database
from config import settings


app = FastAPI()
app.include_router(chat_router)
app.include_router(lights_router)
app.include_router(auth_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

container = AppContainer()


@app.on_event("startup")
@inject
async def startup():
    await database.connect()


@app.on_event("shutdown")
@inject
async def shutdown():
    await database.disconnect()


users_db = [
    {"id": 1, "name": "Vasya", },
    {"id": 2, "name": "Vitya", },
]

chats_db = [
    {"id": 1, "name": "Vasya & Vitya", 'members': [1, 2]},
]


def get_user_by_id(user_id: int) -> dict | None:
    try:
        return next(filter(lambda x: user_id == x['id'], users_db))
    except StopIteration:
        return None


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {'request': request}
    )


@app.get("/chats")
async def users_chats(user: Annotated[dict, Depends(get_user_by_id)]) -> list[dict]:
    return list(filter(lambda x: user['id'] in x['members'], chats_db))


@app.get("/me")
async def me(user: Annotated[dict, Depends(get_user_by_id)]) -> dict:
    return user
