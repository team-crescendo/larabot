import os

import aiohttp
from dotenv import load_dotenv

load_dotenv(verbose=True, override=True)
base_url = os.getenv("FORTE_BASE_URL")
token = os.getenv("FORTE_TOKEN")


async def request(method, endpoint, **kwargs):
    async with aiohttp.request(
        method,
        base_url + endpoint,
        headers={"Authorization": token, "accept": "application/json"},
        **kwargs
    ) as resp:
        return await resp.json(), resp
