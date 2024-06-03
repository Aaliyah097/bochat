import httpx
import asyncio
import aiofiles
import json
import datetime
import time
from config import settings


class Monitor:
    queue = asyncio.Queue()
    is_active = True

    @classmethod
    async def stop(cls):
        cls.is_active = False
        await cls.log("Монитор остановлен")
        await cls._write()

    @classmethod
    async def _write(cls):
        async with aiofiles.open('events.log', mode='a', encoding='utf-8') as file:
            while True:
                try:
                    item = cls.queue.get_nowait()
                    if not item or item is None:
                        break
                    await file.write(str(item) + "\n")
                except asyncio.QueueEmpty:
                    break

    @classmethod
    async def _send_loki(cls):
        logs = []
        while True:
            try:
                item = cls.queue.get_nowait()
                if not item or item is None:
                    break
                logs.append(item)
            except asyncio.QueueEmpty:
                break
        if not logs:
            return
        async with httpx.AsyncClient() as client:
            response = await client.post(
                headers={
                    'Content-Type': 'application/json',
                },
                timeout=1,
                url=settings.loki_endpoint, data=json.dumps({
                    "streams":
                    [
                        {
                            "stream": {
                                "chat": "events"
                            },
                            "values": [
                                [str(int(datetime.datetime.now().timestamp() * 1e9)),
                                 str(item)] for item in logs
                            ]
                        }
                    ]
                })
            )
            print(response.status_code, response.text)

    @classmethod
    async def log(cls, msg: str, chat_id: int | None = None, user_id: int | None = None, unknown: bool = False) -> None:
        payload = ";".join([
            f'{"INFO" if not unknown else "ERROR"}',
            f'msg={str(msg or "")}',
            f'chat={str(chat_id or "")}',
            f'user={str(user_id or "")}',
            f'time={str(time.time())}'
        ])

        await cls.queue.put(payload)

    @classmethod
    async def consume(cls):
        await cls.log("Монитор запущен")
        while cls.is_active:
            await cls._send_loki()
            await asyncio.sleep(1)
