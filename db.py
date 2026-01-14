"""
db.py

Database utility module for PostgreSQL access using psycopg2 connection pooling.

This module:
- Loads database credentials from environment variables
- Initializes a global SimpleConnectionPool
- Provides a generic `safe_query` helper for reusable, parameterized SQL execution

All queries use pooled connections to avoid expensive reconnect overhead.
"""

from psycopg2.pool import SimpleConnectionPool
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ------------------------------------------------------------------------------
# Database configuration
# ------------------------------------------------------------------------------

"""
Dictionary containing PostgreSQL connection parameters.

Values are loaded from environment variables to allow
environment-specific configuration (local, Docker, production, etc.).
"""
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}
# ------------------------------------------------------------------------------
# Connection pool initialization
# ------------------------------------------------------------------------------

"""
Global PostgreSQL connection pool.

- minconn: minimum number of open connections maintained
- maxconn: maximum number of simultaneous connections allowed

The pool is created once per process and reused across all imports.
"""
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_CONFIG
)

def safe_query(
    query: str,
    params: list | tuple = None,
    fetch: str = None,
    insert: bool = False
):
    """
    Execute a parameterized SQL query safely using a pooled connection.

    This function is intended as a reusable helper for:
    - SELECT queries (fetching one or many rows)
    - INSERT / UPDATE / DELETE queries with optional commit

    Args:
        query (str): SQL query string with placeholders (%s)
        params (list | tuple, optional): Parameters to bind to the query
        fetch (str, optional):
            - "one": return a single row
            - "all": return all rows
            - None: return nothing
        insert (bool, optional):
            - If True, commits the transaction before returning the connection

    Returns:
        Any:
            - Query result if fetch is specified
            - "error in query execution" string if an exception occurs
    """
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
        print(e)
        return "error in query execution"

    finally:
        if cur:
            cur.close()
        if conn:
            if insert:
                conn.commit()
            pool.putconn(conn)
