import time
from typing import Union
import json
import jwt
from httpx import AsyncClient
import aiofile
from config import settings
from monitor import Monitor


async def _create_jwt(
        conf_path: str = settings.google_conf_path,
        ttl_sec: int = settings.google_jwt_ttl):
    async with aiofile.async_open(conf_path) as file:
        config = json.loads(await file.read())

    now = int(time.time())
    payload = {
        'iss': config['client_email'],
        'sub': config['client_email'],
        'aud': 'https://oauth2.googleapis.com/token',
        'iat': now,
        'exp': now + ttl_sec,
        'scope': 'https://www.googleapis.com/auth/firebase.messaging'
    }
    additional_headers = {
        'kid': config['private_key_id']
    }
    signed_jwt = jwt.encode(
        payload, config['private_key'], headers=additional_headers, algorithm='RS256')
    return signed_jwt


async def get_access_token() -> Union[str, None]:
    async with AsyncClient() as client:
        response = await client.post(
            settings.google_token_url,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': await _create_jwt()
            }
        )

    if response.status_code != 200:
        await Monitor.log(response.text)
        return
    return response.json().get("access_token")
