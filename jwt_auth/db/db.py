from psycopg2.pool import SimpleConnectionPool
import os
import logging

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
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

if not all(DB_CONFIG.values()):
    logger.error("Missing DB config environment variables.")
    raise RuntimeError("Server configuration error")

try: 

    pool = SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        **DB_CONFIG
    )

except Exception as e:

    logger.error(f"Invalid DB config, or DB Connection error: {str(e)}")
    raise RuntimeError("Server configuration error")

def safe_query(query: str,params: list | tuple = None,fetch: str = None,insert: bool = False):

    conn = None
    cur = None

    try:
        conn = pool.getconn()
        cur = conn.cursor()

        if params:
            cur.execute(query, tuple(params))
        else:
            cur.execute(query)

        if fetch == "one":
            return cur.fetchone()
        elif fetch == "all":
            return cur.fetchall()

    except Exception as e:

        logger.error(f"Error in query execution: {str(e)}")
        
        raise DBError("Error in query execution",500)

    finally:
        if cur:
            cur.close()
        if conn:
            if insert:
                conn.commit()
            pool.putconn(conn)
