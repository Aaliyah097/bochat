import json
from httpx import AsyncClient
from config import settings
from logger import logger


async def send_notification(device_token: str, title: str, text: str, data: dict[str, str], access_token: str):
    if not data:
        data = {}
    text, title = str(text), title

    async with AsyncClient() as client:
        response = await client.post(
            settings.firebase_send_address,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}',
            },
            json={
                'message': {
                    'token': device_token,
                    'notification': {
                        'title': title,
                        'body': text,
                    },
                    'data': data
                }
            })
        if response.status_code != 200:
            logger.error(response.text)
