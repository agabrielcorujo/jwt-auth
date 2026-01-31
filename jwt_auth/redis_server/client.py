"""
client.py

Redis client initialization module.
"""

import os
import redis
from dotenv import load_dotenv

# Load .env ONLY for local/dev environments
# In ECS, env vars are injected automatically
load_dotenv()


class Cache:
    """
    Wrapper class for initializing and storing a Redis client.
    """

    def __init__(self) -> None:
        """
        Initialize the Redis client.

        - Reads REDIS_URL from environment variables
        - Falls back to Docker default if not set
        """
        self.REDIS_URL = os.getenv(
            "REDIS_URL",
            "redis://redis:6379"  # default for docker-compose
        )

        self.redis_client = redis.Redis.from_url(
            self.REDIS_URL,
            decode_responses=True
        )

        # Optional: fail fast if Redis is unreachable
        try:
            self.redis_client.ping()
        except redis.RedisError as e:
            raise RuntimeError("Failed to connect to Redis") from e


# ----------------------------------------------------------------------
# Shared Redis client instance
# ----------------------------------------------------------------------

cache_obj = Cache()
cache = cache_obj.redis_client
