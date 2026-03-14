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
        redis_kwargs = {"decode_responses": True}

        if self.REDIS_URL.startswith("rediss://"):
            # Keep TLS verification strict by default; allow explicit override for local troubleshooting.
            ssl_cert_reqs = os.getenv("REDIS_SSL_CERT_REQS", "required")
            redis_kwargs["ssl_cert_reqs"] = ssl_cert_reqs

            if ssl_cert_reqs.lower() != "none":
                redis_kwargs["ssl_ca_certs"] = os.getenv("REDIS_SSL_CA_CERTS", certifi.where())

        try:
            self.redis_client = redis.from_url(
                self.REDIS_URL,
                **redis_kwargs
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
