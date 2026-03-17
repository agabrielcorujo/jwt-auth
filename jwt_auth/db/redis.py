import logging
import os

import certifi
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class Cache:

    def __init__(self) -> None:

        url = os.getenv("REDIS_URL")

        if not url:
            logger.warning("Missing REDIS_URL, defaulted to local redis.")

        self.REDIS_URL = url

        try:
            self.redis_client = redis.from_url(
                self.REDIS_URL,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Invalid REDIS_URL: {str(e)}")
            raise RuntimeError("Server Configuration Error") from e

    async def connect(self):

        try:
            await self.redis_client.ping()
        except Exception as e:
            logger.error(f"Unable to reach redis: {str(e)}")
            raise RuntimeError("Server Configuration Error") from e

    async def close(self):
        await self.redis_client.aclose()


# ----------------------------------------------------------------------
# Shared Redis client instance
# ----------------------------------------------------------------------

cache_obj = Cache()
cache = cache_obj.redis_client


async def init_cache():
    await cache_obj.connect()


async def close_cache():
    await cache_obj.close()
