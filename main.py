import asyncio
from typing import Annotated
from fastapi import FastAPI, Request, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.repository import Repository
from src.messages import chat_router
from src.sockets_manager import WebSocketBroadcaster
from src.lights.actions import lights_router
from src.lights.repo import LightsRepo
from src.notifications.actions import notifications_router
from src.notifications import consumer
from src.onboarding.preload import preload_assistant_messages
from src.onboarding.actions import onboarding_router
from container import AppContainer
from src.pubsub_manager import RedisClient
from mongo_database import MongoDBClient
from config import settings
from monitor import Monitor


app = FastAPI()
app.include_router(chat_router)
app.include_router(lights_router)
app.include_router(notifications_router)
app.include_router(onboarding_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

container = AppContainer()
Instrumentator().instrument(app).expose(app)


consumer_ = consumer.Consumer(3)


@app.on_event("startup")
async def startup():
    global consumer_
    await RedisClient.connect()
    await MongoDBClient.connect()
    await Repository.create_indexes()

    await preload_assistant_messages()
    asyncio.create_task(consumer_.main())
    asyncio.create_task(Monitor.consume())


@app.on_event("shutdown")
async def shutdown():
    global consumer_

    consumer_.is_active = False

    await RedisClient.disconnect()
    await MongoDBClient.disconnect()
    await Monitor.stop()
