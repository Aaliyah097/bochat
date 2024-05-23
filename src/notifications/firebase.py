import json
from httpx import AsyncClient
from config import settings
from logger import logger


async def send_notification(device_token: str, title: str, message: dict, access_token: str):
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
                        'body': json.dumps(message),
                    },
                }
            })
        if response.status_code != 200:
            logger.error(response.text)
