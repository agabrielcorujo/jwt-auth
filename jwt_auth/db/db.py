import logging
import os
import uuid

import asyncpg

class DBError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

logging.basicConfig(
    level=logging.INFO,  # minimum level to log
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Database configuration
# ------------------------------------------------------------------------------

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

if not all(DB_CONFIG.values()):
    logger.error("Missing DB config environment variables.")
    raise RuntimeError("Server configuration error")

pool: asyncpg.Pool | None = None


async def init_pool():
    global pool

    if pool is not None:
        return

    try:
        pool = await asyncpg.create_pool(
            min_size=1,
            max_size=10,
            statement_cache_size=0,
            **DB_CONFIG
        )

        logger.info("Database pool initialized")

    except Exception as e:
        logger.error(f"DB connection error: {str(e)}")
        raise RuntimeError("Server configuration error")


async def close_pool():
    global pool

    if pool is None:
        return

    await pool.close()
    pool = None


def _coerce_row(row):
    return tuple(str(v) if isinstance(v, uuid.UUID) else v for v in row)


async def safe_query(query, params=None, fetch=None):
    if pool is None:
        logger.error("Database pool is not initialized. Call init_pool() on startup.")
        raise DBError("Server configuration error", 500)

    query_params = tuple(params or ())

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():

                if fetch == "one":
                    row = await conn.fetchrow(query, *query_params)
                    if row is None:
                        return None
                    return _coerce_row(row)

                elif fetch == "all":
                    rows = await conn.fetch(query, *query_params)
                    return [_coerce_row(r) for r in rows]

                else:
                    return await conn.execute(query, *query_params)

    except DBError:
        raise
    except Exception as e:
        logger.error(f"Error in query execution: {str(e)}")
        raise DBError("Server configuration error", 500)
