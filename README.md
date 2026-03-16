# jwt-auth

FastAPI authentication package built around async route handlers, JWT access tokens, Redis-backed refresh tokens, and PostgreSQL user records.

## What This Package Currently Does

- Exposes an `/auth` router for register, login, refresh, logout, and password reset flows.
- Uses async FastAPI handlers all the way through the controller and database/cache layers.
- Stores refresh tokens in Redis for 14 days.
- Sends password reset codes by email through Resend and stores the code in Redis for 2 minutes.
- Hashes passwords with Argon2 and signs access tokens with `HS256`.

## Repo Layout

```text
jwt_auth/
├── __init__.py
├── auth_routes.py
├── controllers/
│   └── auth_controller.py
├── services/
│   └── auth_services.py
├── schemas/
│   └── auth_schema.py
└── db/
    ├── db.py
    └── redis.py
example_app.py
```

## Install

```bash
pip install git+https://github.com/agabrielcorujo/jwt-auth.git
```

Or in `requirements.txt`:

```txt
jwt-auth @ git+https://github.com/agabrielcorujo/jwt-auth.git
```

## Required Startup Pattern

This package is not plug-and-play with only `include_router(...)`. The database pool and Redis client must be initialized during app startup.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from jwt_auth.auth_routes import router as auth_router
from jwt_auth.db.db import close_pool, init_pool
from jwt_auth.db.redis import close_cache, init_cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    await init_cache()
    try:
        yield
    finally:
        await close_cache()
        await close_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
```

`example_app.py` contains this same pattern.

If you need to decode bearer tokens directly:

```python
from jwt_auth.controllers.auth_controller import decode_access_token_controller as decode_access_token
```

## Async Behavior

- Every route in [`jwt_auth/auth_routes.py`](/Users/adriancorujo/Desktop/auth/jwt_auth/auth_routes.py) is `async`.
- Controllers await service-layer calls instead of doing database or cache work inline.
- PostgreSQL access goes through a shared `asyncpg` pool initialized by `init_pool()`.
- Redis access uses `redis.asyncio` and a shared client verified by `init_cache()`.
- Password reset email delivery uses `asyncio.to_thread(...)` because the Resend SDK call is synchronous.
- JWT creation and decoding are synchronous utility calls, but they do not perform I/O.

## Routes

Base prefix: `/auth`

### `POST /auth/register`

Request body:

```json
{
  "email": "user@example.com",
  "password": "plain-text-password",
  "phone": "",
  "first_name": "",
  "last_name": "",
  "street": "",
  "city": "",
  "state": "",
  "zip_code": ""
}
```

Current behavior:

- Creates the user with `role='client'`.
- Returns `{"created": true, "user_id": "<uuid>"}`.
- Returns `409` if the email already exists.
- `phone` is normalized to digits only, and a leading US `1` is stripped from 11-digit numbers.

### `POST /auth/login`

Request body:

```json
{
  "email": "user@example.com",
  "password": "plain-text-password"
}
```

Current behavior:

- Verifies the submitted password against `password_hash`.
- Creates a 15-minute JWT access token.
- Creates an opaque refresh token and stores it in Redis under `refresh:<token>`.
- Sets the refresh token as an HttpOnly cookie.
- Returns:

```json
{
  "access_token": "<jwt>",
  "role": "client",
  "first_name": "",
  "last_name": "",
  "status": "logged in"
}
```

### `POST /auth/refresh`

Current behavior:

- Reads `refresh_token` from the cookie, not the JSON body.
- Looks up `refresh:<token>` in Redis.
- Fetches the user role from PostgreSQL.
- Returns a new access token but does not rotate the refresh token.

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

### `POST /auth/logout`

Current behavior:

- Reads `refresh_token` from the cookie.
- Deletes `refresh:<token>` from Redis if the cookie is present.
- Deletes the cookie with the same `path` and `domain` settings used on login.
- Returns `{"status": "logged out"}`.

### `PATCH /auth/password-reset-request`

Request body:

```json
{
  "email": "user@example.com"
}
```

Current behavior:

- Looks up the user by email.
- If the user exists, generates a 6-digit code.
- Sends the code by email through Resend.
- Stores the code in Redis under `<email>:pass_reset_code` for 120 seconds.
- Returns `{"status": "sent"}` on success.
- Returns `{}` when the email does not exist or email delivery fails.

### `PATCH /auth/validate-password-reset-request`

Request body:

```json
{
  "email": "user@example.com",
  "code": "123456",
  "password": "new-password"
}
```

Current behavior:

- Reads the cached reset code from Redis.
- If the code matches, hashes the new password and updates `users.password_hash`.
- Deletes the reset code after a successful change.
- Returns `{"status": "password_changed"}` on success.
- Returns `{}` when the code is missing, expired, incorrect, or the user update does not succeed.

## Token And Cookie Behavior

Access token details:

- Algorithm: `HS256`
- Claims: `sub`, `role`, `iat`, `exp`, `type`
- Expiration: 15 minutes

Refresh token details:

- Format: opaque random string from `secrets.token_urlsafe(32)`
- Storage: Redis key `refresh:<token>`
- TTL: 14 days

Login cookie details:

- `key="refresh_token"`
- `httponly=True`
- `secure=True`
- `samesite="none"`
- `path="/auth"`
- `domain=os.getenv("DOMAIN")`

## Environment Variables

These values are required for app import and startup:

```env
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
JWT_KEY=...
REDIS_URL=redis://localhost:6379/0
```

These values are required if you use the password reset routes:

```env
RESEND_API_KEY=...
RESEND_FROM_EMAIL=...
```

Optional:

```env
DOMAIN=.example.com
PROJECT_NAME=Project
REDIS_SSL_CA_CERTS=/path/to/ca-bundle.pem
REDIS_SSL_CERT_REQS=required
```

Notes:

- `DB_*` values are read when [`jwt_auth/db/db.py`](/Users/adriancorujo/Desktop/auth/jwt_auth/db/db.py) is imported.
- `JWT_KEY` is read when [`jwt_auth/services/auth_services.py`](/Users/adriancorujo/Desktop/auth/jwt_auth/services/auth_services.py) is imported.
- `REDIS_URL` is effectively required in the current implementation because the Redis client is constructed from it at import time.
- TLS-specific Redis options are only used when `REDIS_URL` starts with `rediss://`.

## Database Requirements

The service queries assume a `users` table with at least these columns:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE users (
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
    role TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
```

To bootstrap the table from this repo, you can run:

```bash
python3 -m jwt_auth.db.db
```

This entrypoint:

- Initializes the asyncpg pool with your `DB_*` environment variables.
- Runs `CREATE TABLE IF NOT EXISTS users (...)`.
- Closes the pool before exiting.

Before using it, make sure `pgcrypto` is enabled in the target database so `gen_random_uuid()` exists:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Operational notes:

- Registration inserts `role='client'`.
- Login expects `password_hash`, `first_name`, `last_name`, and `role` to be present in query results.
- Refresh expects a user row with a valid `role`.

## Codebase Notes

- The route/controller/service split is clean and consistent.
- Database access is centralized in `safe_query(...)`, which wraps each call in a transaction and normalizes UUIDs to strings.
- There are no tests in this repository at the moment.
- The password reset flow is email-based now; the Twilio dependency is present in `pyproject.toml` but is not used by the current implementation.
