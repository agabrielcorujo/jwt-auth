"""
client.py

Redis client initialization module.

This module:
- Reads the Redis connection URL from environment variables
- Initializes a Redis client using redis-py
- Exposes a shared Redis client instance for use across the application

The client is created once per process and reused wherever imported.
"""

import redis
import os


class Cache:
    """
    Wrapper class for initializing and storing a Redis client.

    This class encapsulates:
    - Reading the Redis connection URL from environment variables
    - Creating a Redis client instance using that URL

    Attributes:
        REDIS_URL (str): Connection string for the Redis server
        redis_client (redis.Redis): Initialized Redis client instance
    """

    def __init__(self) -> None:
        """
        Initialize the Redis client.

        - Defaults to a local Redis instance if REDIS_URL is not set
        - Enables `decode_responses` so Redis returns strings instead of bytes
        """
        self.REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

        self.redis_client = redis.Redis.from_url(
            self.REDIS_URL,
            decode_responses=True
        )


# ------------------------------------------------------------------------------
# Shared Redis client instance
# ------------------------------------------------------------------------------

"""
Singleton-style Redis client used throughout the application.

Importing `cache` from this module provides direct access
to the initialized Redis client.
"""
cache_obj = Cache()
cache = cache_obj.redis_client
