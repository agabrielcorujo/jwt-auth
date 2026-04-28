import logging
import os
import uuid
import asyncio
import asyncpg
import json as j
from jwt_auth.db.redis import cache

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


async def safe_query(query, params=None, fetch=None, cache_aside=True):
    if pool is None:
        logger.error("Database pool is not initialized.")
        raise DBError("Server configuration error", 500)

    query_params = tuple(params or ())
    key = f"{query}:{query_params}" if cache_aside else None

    try:
        # ---------- TRY CACHE ----------
        cached_results = None
        if cache_aside:
            try:
                raw = await cache.get(key)
                if raw is not None:
                    cached_results = j.loads(raw)
                    logger.info("RESULTS RETRIEVED FROM CACHE")
            except Exception as e:
                logger.error(str(e))

        cache_hit = cached_results is not None

        # ---------- EARLY RETURN ON CACHE ----------
        if fetch == "one" and cache_hit:
            return _coerce_row(cached_results)

        if fetch == "all" and cache_hit:
            return [_coerce_row(r) for r in cached_results]

        # ---------- DB ----------
        async with pool.acquire() as conn:
            async with conn.transaction():

                if fetch == "one":
                    db_row = await conn.fetchrow(query, *query_params)
                    if db_row is None:
                        return None

                    row = [
                        str(v) if isinstance(v, uuid.UUID) else v
                        for v in db_row.values()
                    ]

                    if cache_aside:
                        try:
                            await cache.setex(key, 2700, j.dumps(row))
                        except Exception as e:
                            logger.error(f"Cache write failed: {e}")

                    return _coerce_row(row)

                elif fetch == "all":
                    db_rows = await conn.fetch(query, *query_params)

                    rows = [
                        [
                            str(v) if isinstance(v, uuid.UUID) else v
                            for v in r.values()
                        ]
                        for r in db_rows
                    ]

                    if cache_aside:
                        try:
                            await cache.setex(key, 2700, j.dumps(rows))
                        except Exception as e:
                            logger.error(f"Cache write failed: {e}")

                    return [_coerce_row(r) for r in rows]

                else:
                    return await conn.execute(query, *query_params)

    except DBError:
        raise
    except Exception as e:
        logger.error(f"Error in query execution: {str(e)}")
        raise DBError("Server configuration error", 500)


async def create_users_table():
    query = """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            street TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            twofa BOOLEAN NOT NULL DEFAULT FALSE,
            role TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
    """
    add_twofa_column_query = """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS twofa BOOLEAN NOT NULL DEFAULT FALSE;
    """

    try:
        await safe_query(query)
        await safe_query(add_twofa_column_query)

    except Exception as e:
        logger.error(str(e))
        raise DBError("Error creating users table", 500)

    print("users table created successfully") 

async def main():
    await init_pool()
    try:
        await create_users_table()
    finally:
        await close_pool()

if __name__ == "__main__":
    asyncio.run(main())
