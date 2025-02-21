import json
from httpx import AsyncClient
from httpx import ReadTimeout, ConnectTimeout
from config import settings
from monitor import Monitor


async def send_notification(device_token: str, title: str, text: str, data: dict[str, str], access_token: str):
    if not data:
        data = {}
    text, title = str(text), title

    async with AsyncClient() as client:
        try:
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
                            'icon': 'assets/icons/android-launchericon-96-96.png'
                        },
                        "apns": {
                            "payload": {
                                "aps": {
                                    "sound": "default"
                                }
                            }
                        },
                        'data': data
                    }
                })
        except (ReadTimeout, ConnectTimeout):
            await Monitor.log("Таймаут подключения к firebase")
            return
        if response.status_code != 200:
            await Monitor.log(response.text)
        await Monitor.log("Уведомление отправлено на устройство")
