from typing import Annotated
from dependency_injector.wiring import inject
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.messages import chat_router
from src.sockets_manager import WebSocketBroadcaster
from src.lights.actions import lights_router
from container import AppContainer
from src.pubsub_manager import RedisClient
from mongo_database import MongoDBClient
# from database import database
from config import settings
# from src.notifications.queue_connector import RabbitMQPool


app = FastAPI()
app.include_router(chat_router)
app.include_router(lights_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

container = AppContainer()
Instrumentator().instrument(app).expose(app)
# rabbitmq_pool = RabbitMQPool()


@app.on_event("startup")
@inject
async def startup():
    await WebSocketBroadcaster.broadcast.connect()
    await RedisClient.connect()
    await MongoDBClient.connect()
    # await database.connect()
    # await rabbitmq_pool.connect()


@app.on_event("shutdown")
@inject
async def shutdown():
    await WebSocketBroadcaster.broadcast.disconnect()
    await RedisClient.disconnect()
    await MongoDBClient.disconnect()
    # await database.disconnect()
    # await rabbitmq_pool.close()
