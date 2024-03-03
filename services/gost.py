import logging
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


async def fetch_all_config(endpoint: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(urljoin(endpoint, "config"))
        logger.info(response.json())
