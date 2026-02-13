
import os
import redis
from jwt_auth.db.db import logger


class Cache:

    def __init__(self) -> None:

        Url = os.getenv("REDIS_URL")

        if not Url:
            logger.warning("Missing REDIS_URL, defaulted to local redis.")

        self.REDIS_URL = Url or "redis://redis:6379"

        try: 
            self.redis_client = redis.Redis.from_url(
                self.REDIS_URL,
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Invalid REDIS_URL:{str(e)}")
            raise RuntimeError("Server Configuration Error")

        # Optional: fail fast if Redis is unreachable
        try:
            self.redis_client.ping()
        except Exception as e:
            logger.error(f"Unable to reach redis:{str(e)}")
            raise RuntimeError("Server Configuration Error")


# ----------------------------------------------------------------------
# Shared Redis client instance
# ----------------------------------------------------------------------

cache_obj = Cache()

cache = cache_obj.redis_client
